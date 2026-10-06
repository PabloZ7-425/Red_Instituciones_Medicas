from apps.historiales.domain.institutions import Institution
from apps.historiales.infrastructure.factory import AdapterFactory


class DatabaseHealthService:
    def execute(self):
        result = {}

        for institution in Institution:
            config = institution.value
            try:
                adapter = AdapterFactory.create(institution)
                adapter.health_check()
                result[config.slug] = {
                    "institution": config.name,
                    "engine": config.engine,
                    "connected": True,
                }
            except Exception as error:
                result[config.slug] = {
                    "institution": config.name,
                    "engine": config.engine,
                    "connected": False,
                    "error": str(error),
                }

        return result
