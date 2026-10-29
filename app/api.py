import logging.config
import os
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict
from sentinelhub.exceptions import SHRateLimitWarning

import naturalness
from app.route import health, imagery
from naturalness.imagery_store_operator import SentinelHubOperator

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    log_level: str = 'INFO'
    conf_path: Path = Path('conf')

    sentinelhub_api_id: str
    sentinelhub_api_secret: str

    # Planet documentation no longer documents the per minute quotas per account tier, but when it did, our tier
    # had a rate limit of 500 PUs/minute (https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/work_items/47#note_103380)
    # which is approx. 50 MCs/minute.
    sentinelhub_mc_limit_per_minute: int = 50

    model_config = SettingsConfigDict(env_file='.env')

    @property
    def sentinel_hub_pu_limit_per_minute(self):
        # Planet converted from 'processing units' to 'monitoring credits', at a rate of roughly 10:1. Until we update
        # our codebase to count MCs instead of PUs, we have this property to smooth the transition.
        # https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/work_items/50
        return self.sentinelhub_mc_limit_per_minute * 10


description = """
# Climate Action Naturalness Utility

The API to the HeiGIT Climate Action Naturalness utility provides an access point to SentinelHub to calculated different
indices linked to naturalness such as the NDVI.
"""

tags_metadata = [
    {
        'name': 'index',
        'description': 'Retrieve, calculate and manipulate different indices.',
    }
]


@asynccontextmanager
async def configure_dependencies(app: FastAPI):
    """
    Initialize all required dependencies and attach them to the FastAPI state.
    Each underlying service utilizes configuration stored in `./.env`.

    :param app: web application instance
    :return: context manager generator
    """
    log.info('Initialising...')
    # the settings must be provided in an .env file or as env vars by the programmer that recreates the cashed data
    # noinspection PyArgumentList
    settings = Settings()

    app.state.imagery_store = SentinelHubOperator(
        api_id=settings.sentinelhub_api_id,
        api_secret=settings.sentinelhub_api_secret,
        pu_quota_per_minute=settings.sentinel_hub_pu_limit_per_minute,
        script_path=settings.conf_path / 'eval_scripts',
        cache_dir=Path('./cache') / 'imagery',
    )

    log.info('Initialisation completed')

    yield


app = FastAPI(
    title='Naturalness Utility',
    summary='Calculate naturalness for user selected areas.',
    description=description,
    version=f'{naturalness.__version__}',
    contact={
        'name': 'Climate Acton Team',
        'url': 'https://heigit.org/climate-action',
    },
    openapi_tags=tags_metadata,
    lifespan=configure_dependencies,
    docs_url=None if os.getenv('DISABLE_SWAGGER', 'False') in ('True', 'true') else '/docs',
    redoc_url=None if os.getenv('DISABLE_SWAGGER', 'False') in ('True', 'true') else '/redoc',
)
app.include_router(imagery.router)
app.include_router(health.router)


def start():
    # the settings must be provided in an .env file or as env vars by the programmer that recreates the cashed data
    # noinspection PyArgumentList
    settings = Settings()
    logging.basicConfig(level=settings.log_level.upper())
    log_config = settings.conf_path / 'logging.yaml'
    with open(log_config) as file:
        logging.config.dictConfig(yaml.safe_load(file))

    # SentinelHub uses warnings.warn to flag rate limit errors, so they only appear in stderr and not in
    # logs (https://github.com/sentinel-hub/sentinelhub-py/issues/588). We make sure to always print such warnings and
    # to capture all warnings to the logging module so we actually see them each time they happen.
    warnings.filterwarnings(
        'always', message='Download rate limit hit', category=SHRateLimitWarning, module='sentinelhub'
    )
    logging.captureWarnings(True)

    log.info('Starting Naturalness Utility')
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('NATURALNESS_UTILITY_API_PORT', 8000)),
        root_path=os.getenv('ROOT_PATH', '/'),
        log_config=str(log_config),
        log_level=settings.log_level.lower(),
        workers=int(os.getenv('NATURALNESS_UVICORN_WORKERS', 1)),
    )


if __name__ == '__main__':
    start()
