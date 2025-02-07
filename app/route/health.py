from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix='/health')


class HealthCheck(BaseModel):
    status: str = 'ok'


@router.get(
    '', status_code=200, summary='Annie, are you ok?', description='Verify whether the application API is operational'
)
async def is_ok() -> HealthCheck:
    return HealthCheck()
