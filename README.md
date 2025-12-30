# Slow API

> The slow learning of FastAPI  
> **But to the right direction**  

- day 0 server memo : client + server + memo, http request + response, cors  
- day 1 access gate : user + token + memos, fake db(memory), signup + login, request + header, http + path query headers body + method, dependency injection, flask(explicit, imperative, request-driven, low-level) vs fastapi(implicit, declarative, contract-driven, high-level), depends + framework, access control, localStorage vs cookie, xss vs csrf  
- day 2 owner control : update + delete (crud on memory), route(http method + path + process), http message(method + path(+query) + version + headers + blank line + (body)), http + tcp + ip + ethernet/wifi + physical layer, https(http + tls)  
- day 3 unified origin : serving staticfiles, origin(protocol + host + port), route shadowing  
- day 4 personal calendar : same structure as the memo service  
- day 5 event control : authorization vs authentication, resource id  
- day 6 shared calendar : data sharing model  
- day 7 project space : from data sharing model to project team model, rbac(role-based access control)  
- day 8 live sync : project channels, http + websocket, pip install "uvicorn[standard]", devtools - network - disable cache, static asset versioning(cache busting)  
- day 8.5 shared control : collaborative edit(update project event + delete project event)  
- day 9 conflict control : optimistic lock  
- day 10 distributed sync : redis, docker run -d --name redis-day10 -p 6379:6379 redis:7, docker exec -it redis-day10 redis-cli, ping(pong), client browser-app server1-redis server-app server2-client browser, separation of redis client thread and websocket event loop, a threading lock is used to protect shared memory accessed by both the event loop and background threads,
only short and synchronous memory operations are allowed inside the lock,
do not perform async or blocking operations while holding this lock  
- day 11 service separation : making spaghetti code readable and growable, make endpoints shorter by moving service logic outside the endpoint  
- day 12 persistence boundary : moving from memory to database, cover memory access with repository function, service function doesn't know the detail of how to save  
- day 13 transaction and consistency : save before publish to avoid ghost events  
- day 14 idempotency and retry : doing the same thing twice safely by using request id  
