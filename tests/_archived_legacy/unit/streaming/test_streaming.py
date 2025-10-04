from datetime import datetime, timezone
import json

from decimal import Decimal
from src.data.collectors.streaming_collector import StreamingDataCollector
from src.streaming import (
from src.streaming.stream_processor import StreamProcessorManager
from unittest.mock import AsyncMock, Mock, patch
import pytest

"""
流式数据处理测试

测试Kafka Producer和Consumer的生产/消费流程，验证Kafka集成的正确性。

✅ 测试环境Mock策略说明：
=====================================

本测试文件使用Mock/Fake对象替代真实Kafka，实现以下目标：
1. 🔄 测试独立性：不依赖外部Kafka服务，测试可以在任何环境运行
2. ⚡ 快速执行：避免网络延迟和Kafka集群启动时间
3. 🛡️ 错误控制：可以模拟各种错误场景进行测试
4. 📊 结果验证：直接验证消息内容和调用逻辑

📚 Mock实现详解：
=====================================

1. FakeKafkaProducer 类：
   - 模拟confluent_kafka.Producer的接口
   - 将消息存储在内存列表中，方便测试验证
   - 支持produce()、poll()、flush()等核心方法
   - 提供delivery_callback回调机制

2. FakeKafkaConsumer 类：
   - 模拟confluent_kafka.Consumer的接口
   - 从预设的消息列表中["消费["]消息["]"]""
   - 支持subscribe()、poll()、commit()等核心方法
   - 可以模拟各种消费场景和错误情况

3. MockMessage 类：
   - 模拟Kafka消息对象
   - 提供value()、error()、topic()等方法
   - 支持正常消息和错误消息的模拟

🔧 在生产环境中的替换方法：
=====================================

要将测试Mock替换为真实Kafka，需要：

1. 环境配置：
   export KAFKA_BOOTSTRAP_SERVERS = "localhost9092[": export KAFKA_GROUP_ID="]football-data-consumers[": 2. 依赖安装：": pip install confluent-kafka["""

3. 代码修改（在非测试环境）：
   - 移除patch装饰器
   - 使用真实的StreamConfig配置
   - 连接到实际的Kafka集群

4. Docker部署示例：
   # docker-compose.yml
   kafka:
    image: confluentinc/cp-kafka
    environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181

⚠️ 错误处理策略：
=====================================

本测试验证了以下错误处理场景：
1. 消息发送失败时返回False而非抛出异常
2. 消息反序列化失败时的安全降级
3. 数据库连接失败时的错误记录
4. 批量操作中部分失败的统计和处理

这确保了在真实环境中即使遇到网络问题、Kafka故障等情况，
系统也能优雅地处理错误，不会导致整个应用崩溃。
"]]"""

    FootballKafkaConsumer,
    FootballKafkaProducer,
    StreamConfig,
    StreamProcessor)
from src.streaming.stream_processor import StreamProcessorManager
# 📦 为测试环境创建的 Fake/Mock Kafka 客户端
# ========================================================
# 这些类模拟了真实 Kafka 客户端的行为，但在测试期间不会与真实的 Kafka broker 通信。
# 这使得测试能够独立于外部服务运行，从而更快、更可靠。
class FakeKafkaProducer:
    """
    🎭 模拟 Kafka Producer
    完全替代 confluent_kafka.Producer，提供相同的接口但不进行实际网络通信。
    所有["发送["]的消息都存储在内存中，方便测试验证。"]"""
    ✅ 主要功能：
    - 存储所有produce调用的消息
    - 模拟delivery_callback回调机制
    - 提供poll()和flush()方法的空实现
    - 🛡️ 增强错误处理：支持模拟发送失败场景
    - 不抛出网络相关异常，确保测试稳定
    🔧 为什么使用Fake替代真实Kafka：
    =================================
    1. 测试独立性：不依赖外部Kafka服务，可在任何环境运行
    2. 快速执行：避免网络延迟和Kafka集群启动时间
    3. 错误控制：可精确控制各种错误场景的模拟
    4. 结果验证：直接访问内存中的消息，便于断言验证
    5. CI/CD友好：GitHub Actions等CI环境无需配置Kafka
    """
    def __init__(self, configs):
        """
        初始化假Kafka生产者
        Args:
        configs: Kafka配置字典（在测试中被忽略）
        """
        self.configs = configs
        self.messages = []  # 存储所有["发送["]的消息["]"]": self.simulate_failure = False  # 🛡️ 用于模拟发送失败的开关"
        self.failure_count = 0  # 🛡️ 记录失败次数
    def produce(self, topic, key, value, callback):
        """
        模拟生产消息到Kafka topic
        Args:
        topic: 目标topic名称
        key: 消息key
        value: 消息内容
        callback: 发送完成后的回调函数
        💡 测试行为：
        - 将消息存储到self.messages列表
        - 🛡️ 支持模拟发送失败场景
        - 立即调用callback模拟发送结果
        - 不进行任何网络操作
        🔧 错误处理逻辑：
        - 当simulate_failure=True时，模拟发送失败
        - 失败时callback接收到错误对象而非None
        - 这确保了代码在真实环境中的错误处理路径得到测试
        """
        # 🛡️ 模拟发送失败场景
        if self.simulate_failure:
            self.failure_count += 1
            if callback:
            # 模拟发送失败，传递错误对象
            error = Exception(f["模拟Kafka发送失败 #{self.failure_count)"])": callback(error, None)  # err=error表示失败["""
            # 抛出异常让producer的try-catch捕获到失败
            raise Exception(f["]模拟Kafka发送失败 #{self.failure_count)"])": return["""
        # 正常发送逻辑
        self.messages.append({"]topic[": topic, "]key[": key, "]value[": value))": if callback:"""
            # 模拟真实回调，传递一个消息对象表示发送成功
            mock_msg = MockMessage(value=value, topic=topic)
            callback(None, mock_msg)  # err=None表示成功
    def poll(self, timeout):
        "]"""
        模拟轮询（处理回调和获取发送状态）
        Args:
        timeout: 轮询超时时间（在测试中被忽略）
        💡 测试行为：直接返回，不做任何处理
        """
    def flush(self, timeout):
        """
        模拟刷新所有待发送消息
        Args:
        timeout: 刷新超时时间（在测试中被忽略）
        Returns:
        int: 剩余未发送消息数量
        🛡️ 增强错误处理：
        - 当模拟失败时，返回失败数量
        - 确保调用者能检测到发送失败的消息
        """
        if self.simulate_failure:
        return self.failure_count
        return 0
    def set_failure_mode(self, enable: bool):
        """
        🛡️ 设置失败模拟模式
        Args:
        enable: 是否启用失败模拟
        💡 测试用法：
        - 用于测试Kafka发送失败时的错误处理逻辑
        - 确保应用在网络问题时能优雅降级
        """
        self.simulate_failure = enable
        if not enable:
        self.failure_count = 0
class FakeKafkaConsumer:
    """
    🎭 模拟 Kafka Consumer
    完全替代 confluent_kafka.Consumer，提供相同的接口但不进行实际网络通信。
    从预设的消息列表中["消费["]消息，模拟真实的消费行为。"]"""
    ✅ 主要功能：
    - 从内存消息列表中按序["消费["]消息["]"]""
    - 支持subscribe()、poll()、commit()等核心方法
    - 🛡️ 可以预设消息来模拟各种消费场景（包括错误场景）
    - 支持错误消息的模拟测试
    🔧 为什么使用Fake替代真实Kafka：
    =================================
    1. 消费控制：可精确控制消费的消息顺序和内容
    2. 错误模拟：能模拟各种消费异常和网络问题
    3. 测试稳定：不受外部Kafka集群状态影响
    4. 性能优化：内存操作比网络消费快数百倍
    5. 场景覆盖：能测试罕见的edge case和错误情况
    """
    def __init__(self, configs):
        """
        初始化假Kafka消费者
        Args:
        configs: Kafka配置字典（在测试中被忽略）
        """
        self.configs = configs
        self.messages = []  # 预设的消息列表，测试时手动填充
        self.position = 0  # 当前消费位置
        self.simulate_errors = False  # 🛡️ 用于模拟消费错误的开关
    def subscribe(self, topics):
        """
        模拟订阅Kafka主题
        Args:
        topics: 要订阅的主题列表
        💡 测试行为：
        - 不进行实际订阅操作
        - 可以在测试中验证是否调用了此方法
        """
    def poll(self, timeout):
        """
        模拟轮询消息
        Args:
        timeout: 轮询超时时间（在测试中被忽略）
        Returns:
        MockMessage或None: 下一条消息，如果没有消息则返回None
        💡 测试行为：
        - 从self.messages列表中按序返回消息
        - 🛡️ 支持模拟各种poll错误场景
        - 自动更新消费位置
        - 当所有消息消费完毕后返回None
        🔧 错误处理逻辑：
        - 可以模拟网络超时、连接失败等场景
        - 确保消费者代码的错误处理路径得到充分测试
        """
        # 🛡️ 模拟消费错误场景
        if self.simulate_errors and self.position % 3 ==1:  # 每3条消息中有1条错误
        error_mock = Mock()
        error_mock.code.return_value = 1  # 模拟网络错误
            return MockMessage(error=error_mock)
        if self.position < len(self.messages):
            msg = self.messages[self.position]
            self.position += 1
            return msg
        return None
    def set_error_mode(self, enable: bool):
        """
        🛡️ 设置错误模拟模式
        Args:
        enable: 是否启用错误模拟
        💡 测试用法：
        - 用于测试Kafka消费错误时的处理逻辑
        - 确保应用在消费异常时能正确重试或跳过
        """
        self.simulate_errors = enable
    def commit(self, msg):
        """
        模拟提交消息偏移量
        Args:
        msg: 要提交的消息对象
        💡 测试行为：
        - 不进行实际偏移量提交
        - 可以在测试中验证是否调用了此方法
        """
    def close(self):
        """
        模拟关闭消费者连接
        💡 测试行为：不进行任何操作
        """
class MockMessage:
    """
    🎭 模拟 Kafka 消息对象
    完全替代confluent_kafka消息对象，提供相同的接口方法。
    可以模拟正常消息和错误消息，满足各种测试场景需求。
    ✅ 主要功能：
    - 存储消息内容、错误信息、元数据
    - 提供value()、error()、topic()等标准方法
    - 支持正常消息和错误消息的模拟
    - 可自定义partition和offset信息
    - 🛡️ 支持复杂错误场景模拟（网络断开、序列化失败等）
    🔧 为什么需要Mock消息对象：
    ===============================
    1. 接口兼容：与confluent_kafka.Message完全一致的API
    2. 错误模拟：可精确控制错误类型和错误码
    3. 数据控制：可模拟任意的消息内容和元数据
    4. 性能优化：内存操作比网络反序列化快得多
    5. 确定性：测试结果不受外部数据源影响
    """
    def __init__(
        self, value=None, error=None, topic="test-topic[", partition=0, offset=0[""""
        ):
        "]]"""
        初始化模拟消息对象
        Args:
        value: 消息内容（bytes或None）
        error: 错误对象（用于模拟消费错误）
        topic: 消息所属的topic名称
        partition: 消息所属的分区号
            offset: 消息在分区中的偏移量
        """
        self._value = value
        self._error = error
        self._topic = topic
        self._partition = partition
        self._offset = offset
    def value(self):
        """
        获取消息内容
        Returns:
        bytes或None: 消息的原始字节内容
        💡 测试用法：
        - 正常消息：返回消息内容字节
        - 错误消息：通常返回None
        """
        return self._value
    def error(self):
        """
        获取消息错误信息
        Returns:
        错误对象或None: 如果消息有错误则返回错误对象，否则返回None
        💡 测试用法：
        - 正常消息：返回None
        - 错误消息：返回Mock错误对象
        """
        return self._error
    def topic(self):
        """
        获取消息所属的topic
        Returns:
        str: topic名称
        """
        return self._topic
    def partition(self):
        """
        获取消息所属的分区号
        Returns:
        int: 分区号
        💡 测试优势：
        - 可模拟不同分区的消息分发情况
        - 用于测试分区负载均衡策略
        """
        return self._partition
    def offset(self):
        """
        获取消息在分区中的偏移量
        Returns:
        int: 偏移量
        💡 测试优势：
        - 可模拟消费进度和偏移量管理
        - 用于测试消费者的commit逻辑
        """
        return self._offset
        @classmethod
    def create_error_message(
        cls, error_code: "int[", error_description = str : """"
        ) -> "]MockMessage[":""""
        "]"""
        🛡️ 创建错误消息的工厂方法
        Args:
        error_code: 错误码 (1=网络错误, 2=序列化错误, 等)
        error_description: 错误描述
        Returns:
        MockMessage: 包含错误信息的消息对象
        💡 测试用法：
        - 可模拟各种具体的Kafka错误场景
        - 用于验证错误处理逻辑的完整性
        """
        error_mock = Mock()
        error_mock.code.return_value = error_code
        error_mock.str.return_value = error_description or f["Kafka error {error_code}"]": return cls(error=error_mock, value=None)"""
        @classmethod
    def create_normal_message(
        cls, data: "dict[", topic = str "]test-topic[", partition = int 0, offset int = 0[""""
        ) -> "]]MockMessage"""
        💡 创建正常消息的工厂方法
        Args:
        data: 要序列化的数据
        topic: topic名称
        partition: 分区号
        offset: 偏移量
        Returns:
            MockMessage: 包含数据的正常消息对象
        💡 测试用法：
        - 快速创建标准格式的测试消息
        - 自动处理JSON序列化，减少测试代码重复
        """
        serialized_data = json.dumps(data).encode("utf-8[")": return cls(": value=serialized_data, topic=topic, partition=partition, offset=offset[""
        )
class TestStreamConfig:
    "]]""测试流配置"""
    def test_stream_config_initialization(self):
        """测试配置初始化"""
        config = StreamConfig()
        assert config.kafka_config is not None
        assert config.kafka_config.bootstrap_servers is not None
        assert config.topics is not None
        assert "matches-stream[" in config.topics[""""
        assert "]]odds-stream[" in config.topics[""""
        assert "]]scores-stream[" in config.topics[""""
    def test_producer_config(self):
        "]]""测试生产者配置"""
        config = StreamConfig()
        producer_config = config.get_producer_config()
        assert "bootstrap.servers[" in producer_config[""""
        assert "]]client.id[" in producer_config[""""
        assert "]]acks[" in producer_config[""""
    def test_consumer_config(self):
        "]]""测试消费者配置"""
        config = StreamConfig()
        consumer_config = config.get_consumer_config()
        assert "bootstrap.servers[" in consumer_config[""""
        assert "]]group.id[" in consumer_config[""""
        assert "]]auto.offset.reset[" in consumer_config[""""
class TestFootballKafkaProducer:
    "]]""测试Kafka生产者"""
    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()
        # 使用 FakeKafkaProducer 替代真实的 Producer
        self.patcher = patch(
        "src.streaming.kafka_producer.Producer[", new=FakeKafkaProducer[""""
        )
        self.mock_producer_class = self.patcher.start()
    def teardown_method(self):
        "]]""清理测试环境"""
        self.patcher.stop()
    def test_producer_initialization(self):
        """测试生产者初始化"""
        producer = FootballKafkaProducer(self.config)
        producer._create_producer()  # 手动触发创建
        assert producer.config ==self.config
        assert isinstance(producer.producer, FakeKafkaProducer)
        @pytest.mark.asyncio
    async def test_send_match_data(self):
        """测试发送比赛数据"""
        producer = FootballKafkaProducer(self.config)
        match_data = {
        "match_id[": 12345,""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]match_time[": datetime.now(timezone.utc)": result = await producer.send_match_data(match_data)": assert result is True[" assert len(producer.producer.messages) ==1"
        sent_message = json.loads(producer.producer.messages[0]"]]value[")": assert sent_message["]data["]"]match_id[" ==12345[""""
        @pytest.mark.asyncio
    async def test_send_odds_data(self):
        "]]""测试发送赔率数据"""
        producer = FootballKafkaProducer(self.config)
        odds_data = {
        "match_id[": 12345,""""
        "]bookmaker[: "Test Bookmaker[","]"""
        "]home_odds[": 2.5,""""
        "]draw_odds[": 3.2,""""
            "]away_odds[": 1.8}": result = await producer.send_odds_data(odds_data)": assert result is True[" assert len(producer.producer.messages) ==1"
        sent_message = json.loads(producer.producer.messages[0]"]]value[")": assert sent_message["]data["]"]bookmaker[" =="]Test Bookmaker["""""
        @pytest.mark.asyncio
    async def test_send_scores_data(self):
        "]""测试发送比分数据"""
        producer = FootballKafkaProducer(self.config)
        scores_data = {
        "match_id[": 12345,""""
        "]home_score[": 2,""""
        "]away_score[": 1,""""
        "]minute[": 90,""""
            "]status[": ["]finished["}": result = await producer.send_scores_data(scores_data)": assert result is True[" assert len(producer.producer.messages) ==1"
        sent_message = json.loads(producer.producer.messages[0]"]]value[")": assert sent_message["]data["]"]home_score[" ==2[""""
        @pytest.mark.asyncio
    async def test_producer_error_handling(self):
        "]]""测试生产者错误处理"""
        producer = FootballKafkaProducer(self.config)
        producer._create_producer()  # 确保 producer 实例已创建
        # 模拟发送失败
        with patch.object(:
            producer.producer, "produce[", side_effect=Exception("]Kafka Error[")""""
        ):
            result = await producer.send_match_data({"]match_id[": 12345))": assert result is False["""
        @pytest.mark.asyncio
    async def test_batch_send(self):
        "]]""测试批量发送"""
        producer = FootballKafkaProducer(self.config)
        batch_data = [{"match_id[": i} for i in range(3)]": results = await producer.send_batch(batch_data, "]match[")": assert results["]success["] ==3[" assert results["]]failed["] ==0[" assert len(producer.producer.messages) ==3["""
        @pytest.mark.asyncio
    async def test_producer_failure_handling(self):
        "]]]"""
        🛡️ 测试生产者失败处理 - 新增的错误处理测试
        目标：验证在模拟的Kafka发送失败场景下，
        系统能否返回安全的结果而不是抛出异常。
        这确保了在真实环境中遇到网络问题或Kafka集群故障时，
        应用程序不会崩溃，而是优雅地处理错误。
        """
        producer = FootballKafkaProducer(self.config)
        producer._create_producer()  # 初始化producer
        # 🛡️ 启用失败模拟模式
        producer.producer.set_failure_mode(True)
        # 测试单条消息发送失败
        match_data = {"match_id[": 12345, "]home_team[": "]Team A[", "]away_team[": "]Team B["}": result = await producer.send_match_data(match_data)"""
        # 验证失败处理：应返回False而不是抛出异常
        assert result is False
        assert len(producer.producer.messages) ==0  # 没有消息被存储
        assert producer.producer.failure_count ==1  # 记录了失败次数
        # 测试批量发送失败
        batch_data = [{"]match_id[": i} for i in range(3)]": batch_results = await producer.send_batch(batch_data, "]match[")""""
        # 验证批量失败处理
        assert batch_results["]success["] ==0[" assert batch_results["]]failed["] ==3[" assert producer.producer.failure_count ==4  # 1 + 3 = 4次失败["""
        # 测试flush在失败模式下的行为
        remaining = producer.producer.flush(10.0)
        assert remaining ==4  # 返回失败数量
        # 恢复正常模式并验证
        producer.producer.set_failure_mode(False)
        result = await producer.send_match_data({"]]]match_id[": 99999))": assert result is True[" assert len(producer.producer.messages) ==1  # 现在有了成功的消息[""
class TestFootballKafkaConsumer:
    "]]]""测试Kafka消费者"""
    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()
        self.patcher = patch(
        "src.streaming.kafka_consumer.Consumer[", new=FakeKafkaConsumer[""""
        )
        self.mock_consumer_class = self.patcher.start()
    def teardown_method(self):
        "]]""清理测试环境"""
        self.patcher.stop()
    def test_consumer_initialization(self):
        """测试消费者初始化"""
        consumer = FootballKafkaConsumer(self.config)
        consumer._create_consumer()  # 手动触发
        assert consumer.config ==self.config
        assert isinstance(consumer.consumer, FakeKafkaConsumer)
        @pytest.mark.asyncio
        @patch("src.streaming.kafka_consumer.DatabaseManager[")": async def test_process_match_message(self, mock_db_manager_class):"""
        "]""测试处理比赛消息"""
        # 🔧 修复AsyncMock协程警告 - 确保session.add和session.commit正确模拟
        mock_session = AsyncMock()
        # 将add设为普通Mock，因为在真实代码中它不是协程
        mock_session.add = Mock()
        # commit在真实代码中是协程，所以保持AsyncMock
        mock_session.commit = AsyncMock()
        mock_db_manager = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager
        mock_db_manager_class.return_value = mock_db_manager
        consumer = FootballKafkaConsumer(self.config)
        message_data = {
        "data[": {""""
        "]match_id[": 12345,""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
            "]match_time[": datetime.now(timezone.utc)": result = await consumer._process_match_message(message_data)": assert result is True[" mock_session.add.assert_called_once()"
        mock_session.commit.assert_called_once()
        @pytest.mark.asyncio
        @patch("]]src.streaming.kafka_consumer.DatabaseManager[")": async def test_process_odds_message(self, mock_db_manager_class):"""
        "]""测试处理赔率消息"""
        # 🔧 修复AsyncMock协程警告 - 确保session.add和session.commit正确模拟
        mock_session = AsyncMock()
        # 将add设为普通Mock，因为在真实代码中它不是协程
        mock_session.add = Mock()
        # commit在真实代码中是协程，所以保持AsyncMock
        mock_session.commit = AsyncMock()
        mock_db_manager = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager
        mock_db_manager_class.return_value = mock_db_manager
        consumer = FootballKafkaConsumer(self.config)
        message_data = {
        "data[": {""""
        "]match_id[": 12345,""""
        "]bookmaker[: "Test Bookmaker[","]"""
        "]home_odds[": 2.5,""""
            "]draw_odds[": 3.2}""""
        }
        result = await consumer._process_odds_message(message_data)
        assert result is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        @pytest.mark.asyncio
        @patch("]src.streaming.kafka_consumer.DatabaseManager[")": async def test_process_scores_message(self, mock_db_manager_class):"""
        "]""测试处理比分消息"""
        # 🔧 修复AsyncMock协程警告 - 确保session.add和session.commit正确模拟
        mock_session = AsyncMock()
        # 将add设为普通Mock，因为在真实代码中它不是协程
        mock_session.add = Mock()
        # commit在真实代码中是协程，所以保持AsyncMock
        mock_session.commit = AsyncMock()
        mock_db_manager = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager
        mock_db_manager_class.return_value = mock_db_manager
        consumer = FootballKafkaConsumer(self.config)
        message_data = {
        "data[": {""""
        "]match_id[": 12345,""""
        "]home_score[": 2,""""
        "]away_score[": 1,""""
            "]minute[": 90}""""
        }
        result = await consumer._process_scores_message(message_data)
        assert result is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        @pytest.mark.asyncio
    async def test_consume_batch(self):
        "]""测试批量消费"""
        consumer = FootballKafkaConsumer(self.config)
        consumer._create_consumer()  # 手动触发
        # 准备模拟消息
        messages = [
        MockMessage(value=json.dumps(
        {"data_type[: "match"", "data["]: 1})""""
        ).encode()
            ),
            MockMessage(value=json.dumps(
                {"]data_type[: "odds"", "data["]: 2})""""
                ).encode()
            )]
        consumer.consumer.messages = messages
        with patch.object(:
            consumer, "]_process_message[", new_callable=AsyncMock[""""
        ) as mock_process:
            mock_process.return_value = True
            results = await consumer.consume_batch(batch_size=2, timeout=1.0)
        assert results["]]processed["] ==2[" assert mock_process.call_count ==2["""
        @pytest.mark.asyncio
    async def test_consumer_error_handling(self):
        "]]]""测试消费者错误处理"""
        consumer = FootballKafkaConsumer(self.config)
        consumer._create_consumer()
        # 模拟包含错误的消息
        error_mock = Mock()
        error_mock.code.return_value = 1  # 非 EOF 错误
        consumer.consumer.messages = [MockMessage(error=error_mock)]
        results = await consumer.consume_batch(batch_size=1, timeout=1.0)
        assert results["failed["] ==1["]"]" assert results["processed["] ==0["]"]""
        @pytest.mark.asyncio
    async def test_consumer_error_simulation(self):
        """
        🛡️ 测试消费者错误模拟 - 新增的错误处理测试
        目标：验证在模拟的Kafka消费错误场景下，
        系统能否正确识别和处理各种消费异常。
        这确保了在真实环境中遇到网络问题或连接失败时，
        消费者能吐略取消费或进行适当的重试。
        """
        consumer = FootballKafkaConsumer(self.config)
        consumer._create_consumer()
        # 添加正常消息和错误消息混合
        normal_message = MockMessage(value = json.dumps({"data_type[: "match"", "data["]: 1})).encode()""""
        )
        consumer.consumer.messages = ["]normal_message[",  # 第1条：正常[": None,  # 第2条：会触发错误模拟[": normal_message,  # 第3条：正常[""
        ]
        # 🛡️ 启用错误模拟模式
        consumer.consumer.set_error_mode(True)
        # 验证错误处理
        with patch.object(:
            consumer, "]]]]_process_message[", new_callable=AsyncMock[""""
        ) as mock_process:
            mock_process.return_value = True
            results = await consumer.consume_batch(batch_size=5, timeout=2.0)
            # 应该有部分成功和部分失败
        assert results["]]processed["] >= 1  # 至少处理了一条正常消息[" assert results["]]failed["] >= 1  # 至少有一条错误[""""
        # 恢复正常模式
        consumer.consumer.set_error_mode(False)
class TestStreamProcessor:
    "]]""测试流处理器"""
    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()
    def test_stream_processor_initialization(self):
        """测试流处理器初始化"""
        processor = StreamProcessor(self.config)
        assert processor.config ==self.config
        assert processor.producer is None  # 初始化时为None，惰性创建
        assert processor.consumer is None  # 初始化时为None，惰性创建
        @pytest.mark.asyncio
    async def test_send_data(self):
        """测试发送数据"""
        with patch(:
            "src.streaming.stream_processor.FootballKafkaProducer["""""
        ) as mock_producer_class = mock_producer AsyncMock()
            mock_producer.send_match_data.return_value = True
            mock_producer_class.return_value = mock_producer
            processor = StreamProcessor(self.config)
            result = await processor.send_data({"]match_id[": 12345), "]match[")": assert result is True[" mock_producer.send_match_data.assert_called_once_with({"]]match_id[": 12345))": def test_consume_data(self):"""
        "]""测试消费数据"""
        with patch(:
            "src.streaming.stream_processor.FootballKafkaConsumer["""""
        ) as mock_consumer_class = mock_consumer Mock()
            mock_consumer.consume_batch = AsyncMock(return_value = {"]processed[": 1, "]failed[": 0)""""
            )
            mock_consumer.subscribe_all_topics = Mock()
            mock_consumer_class.return_value = mock_consumer
            processor = StreamProcessor(self.config)
            results = processor.consume_data(timeout=1.0, max_messages=10)
        assert results["]processed["] ==1[" mock_consumer.subscribe_all_topics.assert_called_once()"""
        @pytest.mark.asyncio
    async def test_health_check(self):
        "]]""测试健康检查"""
        processor = StreamProcessor(self.config)
        # 测试未初始化状态
        health_status = await processor.health_check()
        assert health_status["producer_status["] =="]not_initialized[" assert health_status["]consumer_status["] =="]not_initialized[" assert health_status["]kafka_connection["] is False[""""
        # 测试已初始化状态
        with patch(:
            "]]src.streaming.stream_processor.FootballKafkaProducer["""""
        ) as mock_producer_class = mock_producer Mock()
            mock_producer.producer = Mock()  # 模拟已初始化的 producer
            mock_producer_class.return_value = mock_producer
            processor._initialize_producer()  # 手动初始化
            health_status = await processor.health_check()
        assert health_status["]producer_status["] =="]healthy[" assert health_status["]consumer_status["] =="]not_initialized[" class TestStreamProcessorManager:""""
    "]""测试流处理器管理器"""
    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()
        @patch("src.streaming.stream_processor.StreamProcessor[")": def test_manager_initialization(self, mock_processor_class):"""
        "]""测试管理器初始化"""
        manager = StreamProcessorManager(self.config, num_processors=3)
        assert len(manager.processors) ==3
        assert mock_processor_class.call_count ==3
        @patch("src.streaming.stream_processor.StreamProcessor[")": def test_start_all_processors(self, mock_processor_class):"""
        "]""测试启动所有处理器"""
        # 为每个处理器创建独立的Mock实例
        mock_processors = []
        for i in range(2):
        mock_processor = Mock()
        mock_processor.start = Mock(return_value=True)
        mock_processors.append(mock_processor)
        mock_processor_class.side_effect = mock_processors
        manager = StreamProcessorManager(self.config, num_processors=2)
        result = manager.start_all()
        assert result is True
        # 验证每个处理器的 start 方法都被调用了一次
        for mock_processor in mock_processors:
        mock_processor.start.assert_called_once()
        @patch("src.streaming.stream_processor.StreamProcessor[")": def test_stop_all_processors(self, mock_processor_class):"""
        "]""测试停止所有处理器"""
        # 为每个处理器创建独立的Mock实例
        mock_processors = []
        for i in range(2):
        mock_processor = Mock()
        mock_processor.stop_processing = Mock()
        mock_processors.append(mock_processor)
        mock_processor_class.side_effect = mock_processors
        manager = StreamProcessorManager(self.config, num_processors=2)
        result = manager.stop_all()
        assert result is True
        # 验证每个处理器的 stop_processing 方法都被调用了一次
        for mock_processor in mock_processors:
        mock_processor.stop_processing.assert_called_once()
class TestStreamingDataCollector:
    """测试流式数据收集器"""
    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()
        @patch("src.data.collectors.streaming_collector.FootballKafkaProducer[")""""
        @patch("]src.data.collectors.streaming_collector.DataCollector.__init__[")": def test_streaming_collector_initialization(": self, mock_base_init, mock_producer_class[""
        ):
        "]]""测试流式收集器初始化"""
        mock_base_init.return_value = None
        collector = StreamingDataCollector()
        assert collector.kafka_producer is not None
        mock_producer_class.assert_called_once()
        @pytest.mark.asyncio
    async def test_collect_fixtures_with_streaming(self):
        """测试带流式处理的赛程收集"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class, patch(
            "]src.data.collectors.streaming_collector.DataCollector.__init__[",": return_value=None), patch.object(": StreamingDataCollector, "]collect_fixtures[", new_callable=AsyncMock[""""
        ) as mock_base_collect:
            # 设置 mock 返回值
            from src.data.collectors.base_collector import CollectionResult
            mock_result = CollectionResult(data_source="]]test_source[",": collection_type="]fixtures[",": records_collected=1,": success_count=1,": error_count=0,"
                status="]success[",": collected_data = [{"]fixture[": {"]id[": 1})])": mock_base_collect.return_value = mock_result[": mock_producer = AsyncMock()": mock_producer.send_match_data.return_value = True"
            mock_producer.close = Mock()  # close不是协程方法
            mock_producer_class.return_value = mock_producer
            collector = StreamingDataCollector()
            collector.kafka_producer = mock_producer
            collector.enable_streaming = True
            results = await collector.collect_fixtures_with_streaming(
                league_id=39, season=2024
            )
        assert results.status =="]]success[" assert len(results.collected_data) ==1[""""
        mock_base_collect.assert_called_once_with(league_id=39, season=2024)
        @pytest.mark.asyncio
    async def test_collect_odds_with_streaming(self):
        "]]""测试带流式处理的赔率收集"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class, patch(
            "]src.data.collectors.streaming_collector.DataCollector.__init__[",": return_value=None), patch.object(": StreamingDataCollector, "]collect_odds[", new_callable=AsyncMock[""""
        ) as mock_base_collect:
            # 设置 mock 返回值
            from src.data.collectors.base_collector import CollectionResult
            mock_result = CollectionResult(data_source="]]test_source[",": collection_type="]odds[",": records_collected=1,": success_count=1,": error_count=0,"
                status="]success[",": collected_data = [{"]bookmakers[": [{"]name[": "]test[", "]bets[" []}])])": mock_base_collect.return_value = mock_result[": mock_producer = AsyncMock()": mock_producer.send_odds_data.return_value = True"
            mock_producer.close = Mock()  # close不是协程方法
            mock_producer_class.return_value = mock_producer
            collector = StreamingDataCollector()
            collector.kafka_producer = mock_producer
            collector.enable_streaming = True
            results = await collector.collect_odds_with_streaming(fixture_id=12345)
        assert results.status =="]]success[" assert len(results.collected_data) ==1[""""
        mock_base_collect.assert_called_once_with(fixture_id=12345)
        @pytest.mark.asyncio
    async def test_collect_live_scores_with_streaming(self):
        "]]""测试带流式处理的实时比分收集"""
        with patch(:
            "src.data.collectors.streaming_collector.FootballKafkaProducer["""""
        ) as mock_producer_class, patch(
            "]src.data.collectors.streaming_collector.DataCollector.__init__[",": return_value=None), patch.object(": StreamingDataCollector, "]collect_live_scores[", new_callable=AsyncMock[""""
        ) as mock_base_collect:
            # 设置 mock 返回值
            from src.data.collectors.base_collector import CollectionResult
            mock_result = CollectionResult(data_source="]]test_source[",": collection_type="]live_scores[",": records_collected=1,": success_count=1,": error_count=0,"
                status="]success[",": collected_data=["""
                {"]fixture[": {"]id[": 1}, "]goals[": {"]home[": 2, "]away[": 1})""""
                ])
            mock_base_collect.return_value = mock_result
            mock_producer = AsyncMock()
            mock_producer.send_scores_data.return_value = True
            mock_producer.close = Mock()  # close不是协程方法
            mock_producer_class.return_value = mock_producer
            collector = StreamingDataCollector()
            collector.kafka_producer = mock_producer
            collector.enable_streaming = True
            results = await collector.collect_live_scores_with_streaming()
        assert results.status =="]success[" assert len(results.collected_data) ==1[""""
        mock_base_collect.assert_called_once_with()
class TestKafkaIntegration:
    "]]""测试Kafka集成场景"""
    @pytest.mark.asyncio
    @patch("src.streaming.kafka_consumer.DatabaseManager[")": async def test_end_to_end_flow(self, mock_db_manager_class):"""
        "]""测试端到端流程"""
        config = StreamConfig()
        with patch(:
        "src.streaming.kafka_producer.Producer[", new=FakeKafkaProducer[""""
        ), patch("]]src.streaming.kafka_consumer.Consumer[", new = FakeKafkaConsumer)""""
            # 1. 生产者发送消息
            producer = FootballKafkaProducer(config)
            test_data = {"]match_id[": 12345, "]home_team[": "]Team A["}": result = await producer.send_match_data(test_data)": assert result is True[" assert len(producer.producer.messages) ==1"
        # 2. 消费者接收并处理消息
        consumer = FootballKafkaConsumer(config)
        consumer._create_consumer()
        # 从 FakeProducer 获取消息并放入 FakeConsumer
        sent_message = producer.producer.messages[0]
        consumer.consumer.messages = [MockMessage(value=sent_message["]]value["].encode())]""""
        # 🔧 Mock 数据库 - 修复AsyncMock协程警告
        mock_session = AsyncMock()
        # 将add设为普通Mock，因为在真实代码中它不是协程
        mock_session.add = Mock()
        # commit在真实代码中是协程，所以保持AsyncMock
        mock_session.commit = AsyncMock()
        mock_db_manager = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager
        mock_db_manager_class.return_value = mock_db_manager
        # 重新设置consumer的数据库管理器
        consumer.db_manager = mock_db_manager
        # 验证消息内容格式正确
        message_content = json.loads(sent_message["]value["])": assert "]data_type[" in message_content[""""
        assert "]]data[" in message_content[""""
        # 手动添加缺失的字段到消息中
        if "]]data_type[": not in message_content:": message_content["]data_type["] = "]match[": message_content["]source["] = "]test_source[": updated_message = json.dumps(message_content)": consumer.consumer.messages = [MockMessage(value=updated_message.encode())]"""
        # 消费并验证
        results = await consumer.consume_batch(batch_size=1)
        assert results["]processed["] ==1[""""
        # 验证session的调用
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    def test_data_serialization(self):
        "]]""测试数据序列化"""
        config = StreamConfig()
        with patch("src.streaming.kafka_producer.Producer[", new = FakeKafkaProducer)": producer = FootballKafkaProducer(config)": test_data = {""
            "]match_id[": 12345,""""
            "]match_time[": datetime.now(timezone.utc)": serialized = producer._serialize_data(test_data)": assert isinstance(serialized, str)" deserialized = json.loads(serialized)"
        assert "]match_id[" in deserialized[""""
        @pytest.mark.asyncio
    async def test_async_processing(self):
        "]]""测试异步处理"""
        config = StreamConfig()
        with patch("src.streaming.kafka_producer.Producer[", new = FakeKafkaProducer)": producer = FootballKafkaProducer(config)": batch_data = [{"]match_id[": i} for i in range(5)]": results = await producer.send_batch(batch_data, "]match[")": assert results["]success["] ==5[" if __name__ =="]]__main__[": pytest.main(["]__file__[", "]-v["])"]": from src.data.collectors.base_collector import CollectionResult": from src.data.collectors.base_collector import CollectionResult"
            from src.data.collectors.base_collector import CollectionResult