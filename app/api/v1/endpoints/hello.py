from fastapi import APIRouter, Depends

from app.schemas.hello import HelloResponse
from app.services.hello_service import HelloService

router = APIRouter(prefix="/hello", tags=["hello"])


def get_hello_service() -> HelloService:
    return HelloService()


@router.get("", response_model=HelloResponse)
def read_hello(service: HelloService = Depends(get_hello_service)) -> HelloResponse:
    return HelloResponse(message=service.get_message())
