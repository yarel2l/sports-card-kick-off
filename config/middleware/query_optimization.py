"""
✅ Middleware para detectar y prevenir N+1 queries
"""

import logging
import time
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


class QueryOptimizationMiddleware:
    """
    Middleware para detectar y prevenir N+1 queries
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Inicializar contadores
        start_time = time.time()

        # Verificar si connection.queries está disponible
        try:
            initial_queries = len(connection.queries)
            queries_available = True
        except (AttributeError, TypeError):
            initial_queries = 0
            queries_available = False

        # Procesar la request
        response = self.get_response(request)

        # Calcular métricas
        end_time = time.time()
        duration = end_time - start_time

        if queries_available:
            final_queries = len(connection.queries)
            total_queries = final_queries - initial_queries

            # Detectar posibles N+1 queries (solo si DEBUG está activo)
            if settings.DEBUG:
                self._detect_n_plus_one_queries(
                    connection.queries[initial_queries:], request.path
                )

            # Agregar headers de métricas
            response["X-Query-Count"] = str(total_queries)

            # Log si hay demasiadas queries
            if total_queries > 50:  # Umbral configurable
                logger.warning(
                    f"⚠️ Muchas queries detectadas: {total_queries} queries en {duration:.3f}s "
                    f"para {request.path}"
                )
        else:
            response["X-Query-Count"] = "N/A"

        response["X-Request-Duration"] = f"{duration:.3f}s"

        return response

    def _detect_n_plus_one_queries(self, queries, path):
        """
        Detecta patrones de N+1 queries
        """
        if not queries:
            return

        # Agrupar queries por tipo
        query_patterns = {}
        for query in queries:
            # Skip queries with None sql (can happen with certain operations)
            if not query or not query.get("sql"):
                continue

            sql = query["sql"].strip()
            if sql.startswith("SELECT"):
                # Extraer tabla principal
                table_name = self._extract_table_name(sql)
                if table_name:
                    if table_name not in query_patterns:
                        query_patterns[table_name] = []
                    query_patterns[table_name].append(sql)

        # Detectar patrones N+1
        for table, table_queries in query_patterns.items():
            if len(table_queries) > 10:  # Umbral para N+1
                logger.warning(
                    f"🚨 Posible N+1 query detectado: {len(table_queries)} queries "
                    f"para tabla '{table}' en {path}"
                )

                # Mostrar las primeras 3 queries como ejemplo
                for i, query in enumerate(table_queries[:3]):
                    logger.warning(f"  Query {i+1}: {query[:100]}...")

    def _extract_table_name(self, sql):
        """
        Extrae el nombre de la tabla de una query SQL
        """
        try:
            # Buscar FROM en la query
            from_index = sql.upper().find(" FROM ")
            if from_index == -1:
                return None

            # Extraer después de FROM
            after_from = sql[from_index + 6 :].strip()

            # Buscar el primer espacio o paréntesis
            space_index = after_from.find(" ")
            if space_index == -1:
                space_index = after_from.find("(")

            if space_index == -1:
                return after_from

            table_name = after_from[:space_index].strip()

            # Limpiar alias si existe
            if " AS " in table_name.upper():
                table_name = table_name.split(" AS ")[0].strip()

            return table_name
        except:
            return None
