# Gate — 知微合并开工确认

- [x] 产品名：知微
- [x] 场景：校园舆情（可选演示；主场景为多平台/B 站口碑）
- [x] 前端：Vue 3 + Vite + ECharts
- [x] 存储：一期 SQLite
- [x] 情感：词典快筛 + 中文 BERT（GPU）；OpenAI 兼容 LLM 仅可选报告摘要 / Agent
- [x] 主题：词云 + BERTopic（不用 LDA）
- [x] 趋势：滑动平均 / Prophet（不用 ARIMA）
- [x] 传播：增长率与峰值（不用 SIR）
- [x] 采集：一期文件导入；二期外挂 MediaCrawler + 内嵌 B 站评论
- [x] Agent：一期不做；二期可选
- [x] Phase E：PDF/CSV、可选 OpenAI 兼容 LLM、Prophet、analysis-jobs、敏感词可配置（不做登录/答辩文档）
- [x] Phase F（部分）：外挂 MediaCrawler + 内嵌 B 站评论 + 轻量 Agent（问答/简报）

下一步：可选词典 vs BERT 实验表，或继续打磨演示数据链路。
