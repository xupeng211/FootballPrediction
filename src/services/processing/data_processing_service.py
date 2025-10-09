"""
主数据处理服务

整合所有处理器、验证器和缓存组件，提供统一的数据处理接口。
"""



    FeaturesProcessor,
    MatchProcessor,
    OddsProcessor,
)


class DataProcessingService(EnhancedBaseService):
    """数据处理服务主类"""

    def __init__(self, config: Optional[ServiceConfig] = None):
        """初始化数据处理服务"""
        if config is None:
            config = ServiceConfig(
                name="data_processing",
                version="1.0.0",
                description="数据处理服务"
            )
        super().__init__(config)
        
        # 初始化组件
        self.match_processor = MatchProcessor()
        self.odds_processor = OddsProcessor()
        self.features_processor = FeaturesProcessor()
        self.data_validator = DataValidator()
        self.processing_cache = ProcessingCache()
        
        # 处理统计
        self.processing_stats = {
            "matches_processed": 0,
            "odds_processed": 0,
            "features_generated": 0,
            "validation_errors": 0,
            "cache_hits": 0,
        }

    async def initialize(self) -> None:
        """初始化服务"""
        await super().initialize()
        
        # 初始化缓存
        await self.processing_cache.initialize()
        
        self.logger.info("数据处理服务初始化完成")

    async def shutdown(self) -> None:
        """关闭服务"""
        # 关闭缓存
        await self.processing_cache.shutdown()
        
        await super().shutdown()
        self.logger.info("数据处理服务已关闭")

    async def process_match_data(
        self,
        raw_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        use_cache: bool = True,
        validate: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        处理比赛数据

        Args:
            raw_data: 原始比赛数据
            use_cache: 是否使用缓存
            validate: 是否验证数据

        Returns:
            处理后的比赛数据
        """
        return await self.execute_with_metrics(
            "process_match_data",
            lambda: self._process_match_data_impl(raw_data, use_cache, validate)
        )

    async def _process_match_data_impl(
        self,
        raw_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        use_cache: bool,
        validate: bool,
    ) -> Optional[pd.DataFrame]:
        """处理比赛数据的具体实现"""
        try:
            # 检查缓存
            if use_cache:
                cached_result = await self.processing_cache.get_cached_result(
                    "match_processing", raw_data
                )
                if cached_result is not None:
                    self.processing_stats["cache_hits"] += 1
                    return pd.DataFrame(cached_result)

            # 处理数据
            processed_data = await self.match_processor.process_raw_match_data(raw_data)
            
            if processed_data is None:
                return None

            # 验证数据
            if validate:
                validation_result = await self.data_validator.validate_data_quality(
                    processed_data, "match_data"
                )
                if not validation_result["valid"]:
                    self.processing_stats["validation_errors"] += 1
                    self.logger.error(
                        f"比赛数据验证失败: {validation_result['errors']}"
                    )
                    return None

            # 缓存结果
            if use_cache:
                await self.processing_cache.cache_result(
                    "match_processing", raw_data, processed_data.to_dict("records")
                )

            self.processing_stats["matches_processed"] += len(processed_data)
            return processed_data

        except Exception as e:
            self.logger.error(f"处理比赛数据失败: {e}", exc_info=True)
            return None

    async def process_odds_data(
        self,
        raw_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        use_cache: bool = True,
        validate: bool = True,
        detect_arbitrage: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        处理赔率数据

        Args:
            raw_data: 原始赔率数据
            use_cache: 是否使用缓存
            validate: 是否验证数据
            detect_arbitrage: 是否检测套利机会

        Returns:
            处理后的赔率数据
        """
        return await self.execute_with_metrics(
            "process_odds_data",
            lambda: self._process_odds_data_impl(
                raw_data, use_cache, validate, detect_arbitrage
            )
        )

    async def _process_odds_data_impl(
        self,
        raw_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        use_cache: bool,
        validate: bool,
        detect_arbitrage: bool,
    ) -> Optional[pd.DataFrame]:
        """处理赔率数据的具体实现"""
        try:
            # 检查缓存
            if use_cache:
                cached_result = await self.processing_cache.get_cached_result(
                    "odds_processing", raw_data
                )
                if cached_result is not None:
                    self.processing_stats["cache_hits"] += 1
                    return pd.DataFrame(cached_result)

            # 处理数据
            processed_data = await self.odds_processor.process_raw_odds_data(raw_data)
            
            if processed_data is None:
                return None

            # 检测套利机会
            if detect_arbitrage:
                arbitrage_opportunities = await self.odds_processor.detect_arbitrage_opportunities(
                    processed_data
                )
                if arbitrage_opportunities:
                    self.logger.info(
                        f"发现 {len(arbitrage_opportunities)} 个套利机会"
                    )

            # 验证数据
            if validate:
                validation_result = await self.data_validator.validate_data_quality(
                    processed_data, "odds_data"
                )
                if not validation_result["valid"]:
                    self.processing_stats["validation_errors"] += 1
                    self.logger.error(
                        f"赔率数据验证失败: {validation_result['errors']}"
                    )
                    return None

            # 缓存结果
            if use_cache:
                await self.processing_cache.cache_result(
                    "odds_processing", raw_data, processed_data.to_dict("records")
                )

            self.processing_stats["odds_processed"] += len(processed_data)
            return processed_data

        except Exception as e:
            self.logger.error(f"处理赔率数据失败: {e}", exc_info=True)
            return None

    async def generate_features(
        self,
        match_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        feature_config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        生成特征数据

        Args:
            match_data: 比赛数据
            feature_config: 特征配置
            use_cache: 是否使用缓存

        Returns:
            特征数据
        """
        return await self.execute_with_metrics(
            "generate_features",
            lambda: self._generate_features_impl(match_data, feature_config, use_cache)
        )

    async def _generate_features_impl(
        self,
        match_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        feature_config: Optional[Dict[str, Any]],
        use_cache: bool,
    ) -> Optional[pd.DataFrame]:
        """生成特征数据的具体实现"""
        try:
            # 检查缓存
            if use_cache:
                cached_result = await self.processing_cache.get_cached_result(
                    "features_processing", match_data, feature_config
                )
                if cached_result is not None:
                    self.processing_stats["cache_hits"] += 1
                    return pd.DataFrame(cached_result)

            # 生成特征
            features_data = await self.features_processor.process_features_data(
                match_data, feature_config
            )
            
            if features_data is None:
                return None

            # 验证特征数据
            validation_result = await self.data_validator.validate_data_quality(
                features_data, "features_data"
            )
            if not validation_result["valid"]:
                self.processing_stats["validation_errors"] += 1
                self.logger.warning(
                    f"特征数据验证警告: {validation_result['warnings']}"
                )

            # 缓存结果
            if use_cache:
                await self.processing_cache.cache_result(
                    "features_processing",
                    match_data,
                    features_data.to_dict("records"),
                    feature_config,
                )

            self.processing_stats["features_generated"] += len(features_data)
            return features_data

        except Exception as e:
            self.logger.error(f"生成特征数据失败: {e}", exc_info=True)
            return None

    async def process_batch_data(
        self,
        data_batches: List[Dict[str, Any]],
        data_type: str = "match",
        **kwargs,
    ) -> List[pd.DataFrame]:
        """
        批量处理数据

        Args:
            data_batches: 数据批次列表
            data_type: 数据类型（match/odds/features）
            **kwargs: 其他参数

        Returns:
            处理后的数据列表
        """
        results = []
        
        for i, batch in enumerate(data_batches):
            self.logger.debug(f"处理批次 {i+1}/{len(data_batches)}")
            
            if data_type == "match":
                result = await self.process_match_data(batch, **kwargs)
            elif data_type == "odds":
                result = await self.process_odds_data(batch, **kwargs)
            elif data_type == "features":
                result = await self.generate_features(batch, **kwargs)
            else:
                self.logger.error(f"不支持的数据类型: {data_type}")
                continue
            
            if result is not None:
                results.append(result)
        
        self.logger.info(f"批量处理完成，成功处理 {len(results)}/{len(data_batches)} 个批次")
        return results

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        获取处理统计信息

        Returns:
            处理统计信息
        """
        # 获取缓存统计
        cache_stats = await self.processing_cache.get_cache_stats()
        
        return {
            "processing_stats": self.processing_stats,
            "cache_stats": cache_stats,
            "service_health": await self.health_check(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
        }
        
        # 检查各组件
        try:
            # 检查缓存
            cache_stats = await self.processing_cache.get_cache_stats()
            health_status["components"]["cache"] = {
                "status": "healthy" if cache_stats["cache_enabled"] else "disabled",
                "hit_rate": cache_stats.get("hit_rate", 0),
            }
            
            # 检查处理器
            health_status["components"]["match_processor"] = {"status": "healthy"}
            health_status["components"]["odds_processor"] = {"status": "healthy"}
            health_status["components"]["features_processor"] = {"status": "healthy"}
            health_status["components"]["validator"] = {"status": "healthy"}
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status

    async def clear_cache(self, operation: Optional[str] = None) -> int:
        """
        清理缓存

        Args:
            operation: 要清理的操作类型（None表示全部）

        Returns:
            清理的键数量
        """
        return await self.processing_cache.invalidate_cache(operation)

    def reset_statistics(self) -> None:
        """重置处理统计"""
        self.processing_stats = {
            "matches_processed": 0,
            "odds_processed": 0,
            "features_generated": 0,
            "validation_errors": 0,
            "cache_hits": 0,
        }
        self.logger.info("处理统计已重置")