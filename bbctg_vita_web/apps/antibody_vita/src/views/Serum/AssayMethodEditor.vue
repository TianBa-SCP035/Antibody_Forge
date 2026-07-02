<template>
  <el-popover
    v-model:visible="open"
    placement="bottom-start"
    :width="triggerWidth"
    trigger="click"
    transition="el-zoom-in-top"
    :show-arrow="false"
    :popper-style="{ padding: '6px 0' }"
    @show="syncFromProps"
  >
    <template #reference>
      <div ref="trigger" class="trigger" :class="{ open }">
        <span :class="{ placeholder: !assayMethod }">{{ assayMethod || '请选择检测方法' }}</span>
        <el-icon class="arrow"><ArrowDown /></el-icon>
      </div>
    </template>

    <div v-for="method in methodList" :key="method" class="option">
      <span class="method" :class="{ on: items[method].on }" @click="toggle(method)">{{ method }}</span>
      <div class="detail" :class="{ dim: !items[method].on }">
        <div class="species-wrap">
          <span
            v-for="species in speciesList"
            :key="species"
            class="species"
            :class="{ on: items[method].species.includes(species) }"
            @click="toggleSpecies(method, species)"
          >{{ species }}</span>
        </div>
        <label class="plate">
          <input
            type="text"
            inputmode="numeric"
            :disabled="!items[method].on"
            :value="items[method].plate"
            @input="setPlate(method, $event.target.value)"
          /> 板
        </label>
      </div>
    </div>
  </el-popover>
</template>

<script>
import { ArrowDown } from '@element-plus/icons-vue'
import { ElIcon, ElPopover } from 'element-plus'

const METHOD_LIST = ['FACS', 'ELISA']
const SPECIES_LIST = ['人', '猴', '鼠', '狗', '猫', 'CHOS', '293']
const DEFAULT_SPECIES = ['人', '猴']

function emptyItems() {
  return {
    FACS: { on: false, species: [...DEFAULT_SPECIES], plate: '' },
    ELISA: { on: false, species: [...DEFAULT_SPECIES], plate: '' },
  }
}

function speciesFromSuffix(suffix) {
  const text = String(suffix || '')
  const chosen = []
  const byLength = [...SPECIES_LIST].sort((a, b) => b.length - a.length)
  let index = 0
  while (index < text.length) {
    const matched = byLength.find((s) => text.slice(index).startsWith(s))
    if (!matched) {
      index += 1
      continue
    }
    chosen.push(matched)
    index += matched.length
  }
  return SPECIES_LIST.filter((s) => chosen.includes(s))
}

function parseAssayMethodText(display) {
  const result = {}
  for (const part of String(display || '').split(' + ')) {
    const token = part.trim()
    if (!token) continue
    const upper = token.toUpperCase()
    for (const method of METHOD_LIST) {
      if (upper.startsWith(method)) {
        result[method] = speciesFromSuffix(token.slice(method.length))
        break
      }
    }
  }
  return result
}

function formatAssayMethodText(items) {
  return METHOD_LIST
    .filter((m) => items[m].on)
    .map((m) => {
      const species = SPECIES_LIST.filter((s) => items[m].species.includes(s))
      return `${m}${species.join('')}`
    })
    .join(' + ')
}

function parsePlate(value) {
  const trimmed = String(value || '').trim()
  if (!trimmed) return null
  const n = Number(trimmed)
  return Number.isNaN(n) ? null : n
}

function fromModel(assayMethod, facsPlateCount, elisaPlateCount) {
  const speciesByMethod = parseAssayMethodText(assayMethod)
  const plates = { FACS: facsPlateCount, ELISA: elisaPlateCount }
  const items = emptyItems()
  for (const method of METHOD_LIST) {
    const selected = method in speciesByMethod || plates[method] != null
    if (!selected) continue
    items[method] = {
      on: true,
      species: [...(speciesByMethod[method] ?? [])],
      plate: plates[method] != null ? String(plates[method]) : '',
    }
  }
  return items
}

function toModel(items) {
  const active = METHOD_LIST.filter((m) => items[m].on)
  if (!active.length) {
    return { assayMethod: '', facsPlateCount: null, elisaPlateCount: null }
  }
  return {
    assayMethod: formatAssayMethodText(items),
    facsPlateCount: items.FACS.on ? parsePlate(items.FACS.plate) : null,
    elisaPlateCount: items.ELISA.on ? parsePlate(items.ELISA.plate) : null,
  }
}

export default {
  name: 'AssayMethodEditor',
  components: { ArrowDown, ElIcon, ElPopover },
  props: {
    assayMethod: { type: String, default: '' },
    facsPlateCount: { type: Number, default: null },
    elisaPlateCount: { type: Number, default: null },
  },
  emits: ['update:assayMethod', 'update:facsPlateCount', 'update:elisaPlateCount'],
  data() {
    return {
      methodList: METHOD_LIST,
      speciesList: SPECIES_LIST,
      open: false,
      triggerWidth: 300,
      items: emptyItems(),
    }
  },
  watch: {
    assayMethod: 'syncIfClosed',
    facsPlateCount: 'syncIfClosed',
    elisaPlateCount: 'syncIfClosed',
  },
  mounted() {
    this.$nextTick(() => {
      if (this.$refs.trigger) {
        this.triggerWidth = this.$refs.trigger.offsetWidth
      }
    })
  },
  methods: {
    syncIfClosed() {
      if (!this.open) {
        this.syncFromProps()
      }
    },
    syncFromProps() {
      this.items = fromModel(this.assayMethod, this.facsPlateCount, this.elisaPlateCount)
    },
    toggle(method) {
      const item = this.items[method]
      item.on = !item.on
      if (item.on && !item.species.length) {
        item.species = [...DEFAULT_SPECIES]
      }
      this.commit()
    },
    toggleSpecies(method, species) {
      const item = this.items[method]
      if (!item.on) {
        item.on = true
      }
      const selected = new Set(item.species)
      if (selected.has(species)) {
        selected.delete(species)
      } else {
        selected.add(species)
      }
      item.species = SPECIES_LIST.filter((name) => selected.has(name))
      this.commit()
    },
    setPlate(method, value) {
      const item = this.items[method]
      if (!item.on) {
        item.on = true
      }
      item.plate = value
      this.commit()
    },
    commit() {
      const model = toModel(this.items)
      this.$emit('update:assayMethod', model.assayMethod)
      this.$emit('update:facsPlateCount', model.facsPlateCount)
      this.$emit('update:elisaPlateCount', model.elisaPlateCount)
    },
  },
}
</script>

<style scoped>
.trigger {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  height: 32px;
  padding: 0 30px 0 11px;
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  background: var(--el-fill-color-blank);
  cursor: pointer;
  font-size: 14px;
  color: var(--el-text-color-regular);
  box-sizing: border-box;
}
.trigger:hover { border-color: var(--el-border-color-hover); }
.trigger.open { border-color: var(--el-color-primary); }
.trigger span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trigger .placeholder { color: var(--el-text-color-placeholder); }
.trigger .arrow {
  position: absolute;
  right: 10px;
  color: var(--el-text-color-placeholder);
  transition: transform var(--el-transition-duration);
}
.trigger.open .arrow { transform: rotate(180deg); }

.option { display: flex; align-items: flex-start; min-height: 34px; padding: 6px 12px; }
.option:hover { background: var(--el-fill-color-light); }

.method {
  flex-shrink: 0;
  width: 54px;
  margin-right: 12px;
  padding-right: 12px;
  border-right: 1px solid var(--el-border-color-lighter);
  line-height: 24px;
  cursor: pointer;
  user-select: none;
}
.method.on { color: var(--el-color-primary); }

.detail {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  min-width: 0;
  transition: opacity 0.2s;
}
.detail.dim { opacity: 0.4; }
.option:hover .detail.dim { opacity: 0.65; }

.species-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.species {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
  height: 24px;
  padding: 0 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
  box-sizing: border-box;
}
.species.on {
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-5);
}

.plate {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.plate input {
  width: 36px;
  height: 24px;
  padding: 0 4px;
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  text-align: center;
  font-size: 12px;
  outline: none;
}
.plate input:focus { border-color: var(--el-color-primary); }
.plate input:disabled { background: var(--el-fill-color-light); cursor: not-allowed; }
</style>
