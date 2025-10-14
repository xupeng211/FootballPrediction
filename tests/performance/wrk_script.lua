-- wrk性能测试脚本
-- 模拟真实API请求模式

-- 请求权重配置
local requests = {
    { weight = 30, method = "GET", path = "/api/health" },
    { weight = 20, method = "GET", path = "/api/matches" },
    { weight = 15, method = "GET", path = "/api/teams" },
    { weight = 15, method = "GET", path = "/api/predictions" },
    { weight = 10, method = "GET", path = "/api/statistics" },
    { weight = 5,  method = "GET", path = "/api/leaderboard" },
    { weight = 5,  method = "POST", path = "/api/auth/login", body = '{"username":"test","password":"test"}' }
}

-- 请求计数器
local counter = 1

-- 初始化
function init(args)
    -- 初始化随机种子
    math.randomseed(os.time())
end

-- 生成请求
function request()
    -- 根据权重选择请求
    local total_weight = 0
    for _, req in ipairs(requests) do
        total_weight = total_weight + req.weight
    end

    local rand = math.random(1, total_weight)
    local current_weight = 0
    local selected_request = nil

    for _, req in ipairs(requests) do
        current_weight = current_weight + req.weight
        if rand <= current_weight then
            selected_request = req
            break
        end
    end

    -- 构建请求
    if selected_request.method == "GET" then
        return wrk.format(selected_request.method, selected_request.path)
    elseif selected_request.method == "POST" then
        return wrk.format(selected_request.method, selected_request.path, nil, selected_request.body)
    end
end

-- 响应处理
function response(status, headers, body)
    -- 记录响应状态
    if status >= 500 then
        print("服务器错误: " .. status)
    elseif status >= 400 then
        print("客户端错误: " .. status)
    end

    -- 更新计数器
    counter = counter + 1
end

-- 测试完成时的总结
function done(summary, latency, requests)
    -- 打印性能统计
    print("\n========== 性能测试总结 ==========")
    print("总请求数: " .. summary.requests)
    print("持续时间: " .. summary.duration / 1000000 .. " 秒")
    print("平均响应时间: " .. latency.mean .. " ms")
    print("最大响应时间: " .. latency.max .. " ms")
    print("最小响应时间: " .. latency.min .. " ms")
    print("50%响应时间: " .. latency:percentile(50) .. " ms")
    print("90%响应时间: " .. latency:percentile(90) .. " ms")
    print("95%响应时间: " .. latency:percentile(95) .. " ms")
    print("99%响应时间: " .. latency:percentile(99) .. " ms")
    print("请求/秒: " .. summary.requests / (summary.duration / 1000000))
    print("传输字节: " .. summary.bytes)
    print("================================")
end
