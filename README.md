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

## Nhóm endpoint

Các route dưới đây đều nằm dưới prefix `/api/v1`.

| Nhóm | Endpoint chính |
| --- | --- |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| Users | `GET /users`, `/users/me`; `PATCH /users/me`; `POST /users/me/change-password` |
| Workspaces | `GET`, `POST /workspaces`; `GET`, `PATCH`, `DELETE /workspaces/{id}`; quản lý `/workspaces/{id}/members` |
| Projects | `GET`, `POST /workspaces/{id}/projects`; `GET`, `PATCH`, `DELETE /projects/{id}` |
| Tasks | `GET`, `POST /projects/{id}/tasks`; `GET`, `PATCH`, `DELETE /tasks/{id}` |
| Labels | `GET`, `POST /projects/{id}/labels`; `PATCH`, `DELETE /labels/{id}`; gắn/gỡ tại `/tasks/{task_id}/labels/{label_id}` |
| Comments | `GET`, `POST /tasks/{task_id}/comments`; `DELETE /comments/{comment_id}` |

## Quyền truy cập

| Tài nguyên | VIEWER | EDITOR | OWNER | ADMIN |
| --- | --- | --- | --- | --- |
| Workspace | Đọc | Đọc | Đọc, đổi tên, xóa | Bypass quyền workspace |
| Thành viên | Đọc danh sách; tự rời workspace | Đọc danh sách; tự rời workspace | Thêm/xóa thành viên; tự rời workspace* | Bypass quyền workspace |
| Project | Đọc | Đọc, tạo, cập nhật/archive | Đọc, tạo, cập nhật/archive, xóa | Bypass quyền workspace |
| Task | Đọc | Đọc, tạo, cập nhật, xóa | Đọc, tạo, cập nhật, xóa | Bypass quyền workspace |
| Label | Đọc | Đọc, tạo, cập nhật, xóa, gắn/gỡ | Đọc, tạo, cập nhật, xóa, gắn/gỡ | Bypass quyền workspace |
| Comment | Đọc; xóa comment của mình | Đọc, tạo; xóa comment của mình | Đọc, tạo; xóa comment của mình hoặc người khác | Bypass quyền workspace |
| Danh sách user hệ thống | Không truy cập | Không truy cập | Không truy cập | Truy cập endpoint admin |

`ADMIN` là role cấp hệ thống và bypass kiểm tra role trong workspace. Các thao tác quản lý user chỉ dành cho admin; user thường chỉ xem và cập nhật hồ sơ của chính mình. *Workspace owner không thể tự rời workspace; cần xóa workspace hoặc chuyển quyền sở hữu (nếu tính năng này được bổ sung sau).

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
- `dependencies.py`: cung cấp session, service và user đã xác thực cho router.
- `main.py`: khởi tạo FastAPI, Redis, router và xử lý exception nghiệp vụ.

## Chạy bằng Docker

Chạy toàn bộ stack (API, MySQL, Redis) từ file `.env` đã tạo ở trên:

```bash
docker compose up -d --build
docker compose ps
```

API chạy tại <http://127.0.0.1:8000> (đổi bằng `APP_PORT` trong `.env`). Container `app` tự chạy
`alembic upgrade head` trước khi khởi động server. MySQL trên máy host vẫn dùng cổng `MYSQL_PORT`
(mặc định 3308), còn app trong container kết nối tới service `mysql:3306` và `redis:6379`.

Dừng stack mà giữ dữ liệu: `docker compose down`. Xóa cả dữ liệu MySQL: `docker compose down -v`.

## Cache và thông báo

- `GET /api/v1/projects/{project_id}/tasks` được cache trong Redis. Mỗi version là một hash
  `project:{id}:tasks:v{version}`; key `project:{id}:tasks:version` giữ version hiện tại. Mỗi tổ hợp
  bộ lọc và phân trang là một field, TTL 300 giây.
- Quyền truy cập luôn được kiểm tra trước khi đọc cache.
- Khi task hoặc label thay đổi, version tăng; request đọc dữ liệu cũ đang chạy chỉ có thể ghi vào
  key version cũ. Các hash cũ tự hết hạn sau 300 giây.
- Nếu Redis không khả dụng, API vẫn đọc trực tiếp từ database và ghi log cảnh báo.
- `REDIS_SOCKET_TIMEOUT` và `REDIS_SOCKET_CONNECT_TIMEOUT` cấu hình thời gian chờ Redis; mặc định 1 giây.
- Khi một thành viên được gán làm người thực hiện task (và không phải chính người thao tác),
  một thư được gửi nền. Hiện thư chỉ được ghi vào log `task_hub.notifications`, chưa có SMTP.
