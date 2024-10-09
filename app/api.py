import os
import logging.config
from pathlib import Path
import yaml
from contextlib import asynccontextmanager

from omegaconf import OmegaConf
import uvicorn
from fastapi import FastAPI

from app.route import imagery, health
from datafusion.imagery_store_operator import resolve_imagery_store


ROOT_PATH = Path(os.path.abspath(__file__)).parent.parent

log_level = os.getenv('LOG_LEVEL', 'INFO')
log_config = f'{ROOT_PATH}/conf/logging.yaml'
log = logging.getLogger(__name__)


@asynccontextmanager
async def configure_dependencies(app: FastAPI):
    """
    Initialize all required dependencies and attach them to the FastAPI state.
    Each underlying service utilizes configuration stored in `./.env`.

    :param app: web application instance
    :return: context manager generator
    """
    log.info('Initialising...')

    cfg = OmegaConf.load('settings.yaml')
    app.state.imagery_store = resolve_imagery_store(cfg, cache_dir=Path('./.cache'))

    log.info('Initialisation completed')

    yield


app = FastAPI(lifespan=configure_dependencies)
app.include_router(health.router)
app.include_router(imagery.router)


if __name__ == '__main__':
    logging.basicConfig(level=log_level.upper())
    with open(log_config) as file:
        logging.config.dictConfig(yaml.safe_load(file))

    log.info('Starting Datafusion Utility')
    uvicorn.run(
        'api:app',
        host='0.0.0.0',
        port=int(os.getenv('DATAFUSION_UTILITY_API_PORT', 8000)),
        root_path=os.getenv('ROOT_PATH', '/'),
        log_config=log_config,
        log_level=log_level.lower(),
        workers=int(os.getenv('DATAFUSION_UVICORN_WORKERS', 1)),
    )
