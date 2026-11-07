# TaskHub

TaskHub là API quản lý công việc được xây dựng bằng FastAPI

## Yêu cầu

- Python 3.13 trở lên
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Cài `uv` trên Windows bằng PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Kiểm tra cài đặt:

```bash
uv --version
```

## Cài đặt project

```
git clone https://github.com/hahuy1708/task-hub.git
```

Mở terminal tại thư mục `task-hub/` (thư mục chứa `pyproject.toml`) và chạy:

```bash
uv sync
```

Lệnh này tạo môi trường `.venv` nếu chưa có và cài dependency từ `pyproject.toml` cùng `uv.lock`, bao gồm các công cụ dev `pytest`, `ruff` và `mypy`.


Tạo file cấu hình local từ mẫu:

```bash
cp .env.example .env
```

Sau đó điền đầy đủ thông tin vào file `.env`

Tạo `JWT_SECRET_KEY` riêng cho máy của bạn (không dùng giá trị mẫu):

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Sao chép kết quả vào `JWT_SECRET_KEY` trong `.env`. Không commit file `.env`.

Tạo bảng từ migration:

```bash
uv run alembic upgrade head
```

Chạy API:

```bash
uv run fastapi dev src/task_hub/main.py
```


## API docs

API chạy tại <http://127.0.0.1:8000> sau khi làm theo bước Chạy API ở trên.

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/health>

Đăng ký qua `POST /api/v1/auth/register`, đăng nhập bằng `POST /api/v1/auth/login`,
rồi dán `access_token` vào **Authorize** trong Swagger UI. Các endpoint `/api/v1/tasks`
và `/api/v1/users/me` yêu cầu Bearer token. `POST /api/v1/auth/refresh` cấp cặp token
mới và thu hồi refresh token cũ; `POST /api/v1/auth/logout` thu hồi refresh token.
Tài khoản đăng ký mặc định có role `MEMBER`; `GET /api/v1/users` chỉ dành cho `ADMIN`.
Để cấp quyền admin ban đầu, đăng ký tài khoản rồi chạy trong MySQL Workbench:

```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'your-email@example.com';
```

Dừng server bằng `Ctrl+C`.

## Chạy kiểm tra

Test dùng một file SQLite tạm riêng cho mỗi test; không kết nối MySQL và không cần cấu hình
database test. Khởi động MySQL chỉ cần khi chạy ứng dụng hoặc migration.

```bash
uv run pytest
```

Các kiểm tra tĩnh:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## Cấu trúc mã nguồn

```text
src/task_hub/
├── dependencies.py
├── main.py
├── models/
├── routers/
├── repositories/
├── schemas/
└── services/

tests/
```

- `models/`: entity và enum của Task.
- `schemas/`: kiểm tra dữ liệu vào và định dạng dữ liệu trả về.
- `services/`: thao tác và quy tắc nghiệp vụ.
- `repositories/`: thao tác với cơ sở dữ liệu.
- `routers/`: các HTTP endpoint.
- `dependencies.py`: cung cấp `TaskService` cho router.
- `main.py`: khởi tạo FastAPI, đăng ký router và xử lý lỗi 404.
