from django.contrib.postgres.indexes import PostgresIndex
from django.db.backends.ddl_references import Statement


class HnswIndex(PostgresIndex):
    suffix = "hnsw"

    def __init__(self, *expressions, m=None, ef_construction=None, **kwargs):
        self.m = m
        self.ef_construction = ef_construction
        super().__init__(*expressions, **kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.m is not None:
            kwargs["m"] = self.m
        if self.ef_construction is not None:
            kwargs["ef_construction"] = self.ef_construction
        return path, args, kwargs

    def get_with_params(self):
        params = []
        if self.m is not None:
            params.append("m = %d" % self.m)
        if self.ef_construction is not None:
            params.append("ef_construction = %d" % self.ef_construction)
        return params

    def create_sql(self, model, schema_editor, **kwargs):
        if schema_editor.connection.vendor != "postgresql":
            return Statement("SELECT 1")
        return super().create_sql(model, schema_editor, **kwargs)

    def remove_sql(self, model, schema_editor, **kwargs):
        if schema_editor.connection.vendor != "postgresql":
            return Statement("SELECT 1")
        return super().remove_sql(model, schema_editor, **kwargs)
