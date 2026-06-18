"""
Run a scraping agent against a LIVE site for manual validation and selector
tuning — the bridge between fixture-based unit tests and real-world data.

This requires outbound network access and a Playwright browser
(``playwright install chromium``); it is NOT part of the automated test suite.

Examples
--------
    python manage.py scrape_live ebay "2018 Prizm Luka Doncic PSA 10"
    python manage.py scrape_live 130point "Mike Trout rookie" --dump-html /tmp/130.html
    python manage.py scrape_live goldin "Jordan rookie" --no-llm

Use ``--dump-html`` to save the raw page so selectors can be tuned offline
against the exact HTML the live site returns.
"""

import asyncio

from django.core.management.base import BaseCommand, CommandError

from apps.scraping.agents import registry


class Command(BaseCommand):
    help = "Run a scraping agent against a live site (manual validation / selector tuning)."

    def add_arguments(self, parser):
        parser.add_argument('source', help=f"Source slug ({', '.join(registry.available_slugs())})")
        parser.add_argument('query', help="Search query, e.g. '2018 Prizm Luka Doncic PSA 10'")
        parser.add_argument('--no-llm', action='store_true', help="Use traditional parsing only")
        parser.add_argument('--limit', type=int, default=10, help="Max items to print")
        parser.add_argument('--dump-html', metavar='FILE', help="Save the raw search page HTML to FILE")

    def handle(self, *args, **options):
        source = options['source']
        query = options['query']

        if source not in registry.available_slugs():
            raise CommandError(
                f"Unknown source '{source}'. Available: {', '.join(registry.available_slugs())}"
            )

        agent_cls = registry.get_agent(source)
        agent = agent_cls(use_llm=not options['no_llm'])

        if options['dump_html']:
            self._dump_html(agent, query, options['dump_html'])

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Scraping '{source}' live for: {query!r} (use_llm={not options['no_llm']})"
        ))
        try:
            result = asyncio.run(agent.scrape(query))
        except Exception as e:
            raise CommandError(
                f"Live scrape failed: {type(e).__name__}: {e}\n"
                "Live scraping needs network access and a Playwright browser "
                "('playwright install chromium')."
            )

        self._report(result, options['limit'])

    def _dump_html(self, agent, query, path):
        from apps.scraping.fetchers import BaseFetcher

        url = agent.build_search_url(query)
        self.stdout.write(f"Fetching raw HTML: {url}")

        async def fetch():
            fetcher = BaseFetcher(headless=True, timeout=agent.timeout, max_retries=agent.max_retries)
            await fetcher.start()
            try:
                return await fetcher.fetch_page(url)
            finally:
                await fetcher.close()

        try:
            html = asyncio.run(fetch())
        except Exception as e:
            raise CommandError(f"Failed to fetch raw HTML: {type(e).__name__}: {e}")

        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(html)
        self.stdout.write(self.style.SUCCESS(f"Saved {len(html)} bytes to {path}"))

    def _report(self, result, limit):
        success = getattr(result, 'success', False)
        items = getattr(result, 'items', []) or []
        total = getattr(result, 'total_results', None)

        style = self.style.SUCCESS if success else self.style.ERROR
        self.stdout.write(style(
            f"success={success}  parsed_items={len(items)}  total_results={total}"
        ))

        metadata = getattr(result, 'metadata', None)
        if metadata is not None:
            for err in getattr(metadata, 'errors', []) or []:
                self.stdout.write(self.style.WARNING(f"  error: {err}"))

        if not items:
            self.stdout.write(self.style.WARNING(
                "No items parsed. If the page loaded, the selectors likely need "
                "tuning — re-run with --dump-html to inspect the live HTML."
            ))
            return

        self.stdout.write("")
        for i, item in enumerate(items[:limit], 1):
            title = getattr(item, 'title', '')
            price = getattr(getattr(item, 'price', None), 'amount', None)
            grade = getattr(getattr(item, 'grade', None), 'grade', None)
            self.stdout.write(f"  {i:>2}. ${price}  {grade or '-':<10}  {title[:80]}")

        if len(items) > limit:
            self.stdout.write(f"  ... and {len(items) - limit} more")
