# poi-equip-ships-data

舰队 Collection 装备→舰娘映射数据服务，通过 GitHub Pages 提供 REST API。

## API 端点

| 端点 | 说明 |
|------|------|
| `https://yuki.github.io/poi-equip-ships-data/index.json` | 元数据（更新时间、条目数） |
| `https://yuki.github.io/poi-equip-ships-data/initial_equip_ships.json` | 完整数据（~30KB） |

### index.json

```json
{
  "updated_at": "2026-05-12T04:00:00Z",
  "equip_count": 233,
  "ship_entry_count": 1273
}
```

### initial_equip_ships.json

```json
{
  "1": [{ "name": "占守", "level": 1 }, { "name": "国後", "level": 1 }],
  "3": [{ "name": "朝潮改", "level": 20 }]
}
```

## 部署步骤

### 1. 创建 GitHub 仓库

在 GitHub 上创建仓库 `yuki/poi-equip-ships-data`（Public）。

### 2. 推送代码

```bash
cd poi-equip-ships-data
git remote add origin git@github.com:yuki/poi-equip-ships-data.git
git add -A
git commit -m "init: equipment-ships data service"
git push -u origin main
```

### 3. 启用 GitHub Pages

Settings → Pages：

- **Source**: Deploy from a branch
- **Branch**: `gh-pages` / `/ (root)`
- Save

> `gh-pages` 分支将在首次 CI 运行时自动创建，无需手动创建。

### 4. 首次触发数据同步

Actions → Sync Equipment Data → **Run workflow** → Run workflow

首次运行会：
1. Clone `yukikuri/akashi-list`
2. 运行 `scripts/extract.js` 提取装备→舰娘数据
3. 生成 `index.json` 元数据
4. 通过 `peaceiris/actions-gh-pages` 推送到 `gh-pages` 分支

### 5. 验证

```bash
curl https://yuki.github.io/poi-equip-ships-data/index.json
curl https://yuki.github.io/poi-equip-ships-data/initial_equip_ships.json
```

> Pages 首次部署后可能需要 1-2 分钟生效。

### 6. 插件连接

在 `poi-plugin-leveling-plan` 的 `services/equip-sync-service.es` 中，确认 `PAGES_BASE` 常量指向正确地址：

```js
const PAGES_BASE = 'https://yuki.github.io/poi-equip-ships-data'
```

## 更新机制

| 触发方式 | 说明 |
|---------|------|
| **定时** | 每日 UTC 4:00 自动执行 |
| **手动** | Actions → Sync Equipment Data → Run workflow |

每次更新会重新 clone akashi-list、提取数据、生成 JSON，如有变化则推送到 `gh-pages`。

`force_orphan: true` 保证 `gh-pages` 分支永远只有 1 个 commit，不堆积历史。

## 文件结构

```
main 分支 (开发维护)
├── scripts/extract.js              # 从 akashi-list HTML 提取数据
└── .github/workflows/sync.yml      # CI: cron + dispatch

gh-pages 分支 (CI 自动生成，对外 API)
├── index.json
└── initial_equip_ships.json
```
