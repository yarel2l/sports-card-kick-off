from django.test import SimpleTestCase

from apps.catalog.services.title_parser import parse_title


class TitleParserTests(SimpleTestCase):
    def test_full_basketball_title(self):
        p = parse_title(
            '2018-19 Panini Prizm Luka Doncic #280 Silver PSA 10 Rookie RC'
        )
        self.assertEqual(p.year, 2018)
        self.assertEqual(p.year_display, '2018-19')
        self.assertEqual(p.brand, 'Panini')
        self.assertEqual(p.set_name, 'Prizm')
        self.assertEqual(p.player_name, 'Luka Doncic')
        self.assertEqual(p.card_number, '280')
        self.assertEqual(p.parallel, 'Silver')
        self.assertEqual(p.grading_company, 'PSA')
        self.assertEqual(p.grade, '10')
        self.assertTrue(p.is_rookie)
        self.assertFalse(p.is_autograph)

    def test_player_first_ordering(self):
        p = parse_title('Luka Doncic 2018 Panini Prizm #280 BGS 9.5')
        self.assertEqual(p.player_name, 'Luka Doncic')
        self.assertEqual(p.grading_company, 'BGS')
        self.assertEqual(p.grade, '9.5')

    def test_multiword_set_does_not_leak_into_player(self):
        p = parse_title('2003 Topps Chrome LeBron James #111 Refractor Rookie PSA 9')
        # "Topps Chrome" must not leave "Chrome" in the player name.
        self.assertEqual(p.player_name, 'Lebron James')
        self.assertEqual(p.set_name, 'Topps Chrome')
        self.assertEqual(p.brand, 'Topps')
        self.assertEqual(p.parallel, 'Refractor')

    def test_autograph_and_serial(self):
        p = parse_title('2021 Bowman Chrome Julio Rodriguez Auto /99 BGS 9.5 Rookie')
        self.assertEqual(p.player_name, 'Julio Rodriguez')
        self.assertTrue(p.is_autograph)
        self.assertEqual(p.serial_limit, 99)
        self.assertEqual(p.set_name, 'Bowman Chrome')

    def test_brand_without_known_set(self):
        p = parse_title('1986 Fleer Michael Jordan #57 RC PSA 8')
        self.assertEqual(p.brand, 'Fleer')
        self.assertIsNone(p.set_name)
        self.assertEqual(p.player_name, 'Michael Jordan')
        self.assertEqual(p.card_number, '57')
        self.assertTrue(p.is_rookie)

    def test_brand_inferred_from_set(self):
        p = parse_title('2020 Prizm Justin Herbert #325 Blue')
        # "Prizm" implies the Panini brand even when not stated.
        self.assertEqual(p.set_name, 'Prizm')
        self.assertEqual(p.brand, 'Panini')

    def test_grading_company_alias_normalized(self):
        p = parse_title('2019 Topps Mike Trout #1 Beckett 9.5')
        self.assertEqual(p.grading_company, 'BGS')
        self.assertEqual(p.grade, '9.5')

    def test_gem_mint_descriptor_between_company_and_grade(self):
        p = parse_title('2018 Panini Prizm Trae Young #78 PSA GEM MT 10')
        self.assertEqual(p.grading_company, 'PSA')
        self.assertEqual(p.grade, '10')

    def test_letter_prefixed_card_number(self):
        p = parse_title('2021 Bowman Chrome Draft Druw Jones #BDC-150 Auto')
        self.assertEqual(p.card_number, 'BDC-150')

    def test_memorabilia_detection(self):
        p = parse_title('2015 National Treasures Patch Auto Karl-Anthony Towns /99')
        self.assertTrue(p.is_memorabilia)
        self.assertTrue(p.is_autograph)
        self.assertEqual(p.serial_limit, 99)

    def test_empty_title(self):
        p = parse_title('')
        self.assertIsNone(p.year)
        self.assertIsNone(p.player_name)

    def test_to_dict(self):
        p = parse_title('2018 Panini Prizm Luka Doncic #280')
        d = p.to_dict()
        self.assertEqual(d['player_name'], 'Luka Doncic')
        self.assertEqual(d['card_number'], '280')
