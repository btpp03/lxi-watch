# lxi-watch

用 GitHub Actions 盯 [LXI.be](https://lxi.be) 免费主机 `btpp03.lxi.be` 的开通状态。

- LXI 官方提示：邮箱确认后建站最长 24 小时。
- 每次运行：查 DNS A 记录 + HTTPS 首页 + 登录面板看服务是否已可管理。
- **只有真开通才推 Telegram**，之后静默（`state.json` 记住）。
- 定时腿是 cron-job.org 外部触发，仓库里没有 `on: schedule`（本账号 GA 原生 cron 不 fire）。

手动跑：Actions → lxi-watch → Run workflow（`source` 留空 = 无论通没通都推一条现状）。

需要的 secrets：`TG_BOT_TOKEN`、`TG_CHAT_ID`、`LXI_EMAIL`、`LXI_PW`。
