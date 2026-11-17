import { register } from 'node:module'

// 仅由 package.json 的 test 脚本通过 --import 加载，生产构建不引用
register('./loader.mjs', import.meta.url)
