# Day 1: Core Setup & Architecture

## Nội dung

- Skeleton: FastAPI app, lifespan, APIRouter versioning /api/v1, GET /health
- Layered Architecture: schemas / models / services / routers
- Resource Task: CRUD (POST, GET list, GET by id, PATCH, DELETE)
- Pydantic v2 schemas, Dependency Injection (Depends)

## Endpoints

1. POST /api/v1/tasks/

![create-task](images/post-task.png)

2. GET /api/v1/tasks/

![get-task](images/get-task.png)

3. PATCH /api/v1/tasks/{task_id}

![update-task](images/update-task.png)

4. GET /api/v1/tasks/{task_id}

![get-task-by-id](images/get-task-by-id.png)


5. DELETE /api/v1/tasks/{task_id}

![alt text](images/delete-task.png)

6. GET /health

![alt text](images/health.png)