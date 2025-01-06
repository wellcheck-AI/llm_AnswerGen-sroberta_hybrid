from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def test_stage_home():
    return {"message": "This is the test stage endpoint!"}

@router.get("/health")
def test_health():
    return {"status": "Test stage is healthy"}