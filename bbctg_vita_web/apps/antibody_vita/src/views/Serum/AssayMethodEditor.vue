<template>
  <el-popover
    v-model:visible="open"
    placement="bottom-start"
    :width="triggerWidth"
    trigger="click"
    transition="el-zoom-in-top"
    :show-arrow="false"
    :popper-style="{ padding: '6px 0' }"
    @show="loadConfig"
  >
    <template #reference>
      <div ref="trigger" class="trigger" :class="{ open }">
        <span :class="{ placeholder: !display }">{{ display || '请选择检测方法' }}</span>
        <el-icon class="arrow"><ArrowDown /></el-icon>
      </div>
    </template>

    <div v-for="method in methodList" :key="method" class="option">
      <span class="method" :class="{ on: items[method].on }" @click="toggle(method)">{{ method }}</span>
      <div class="detail" :class="{ dim: !items[method].on }">
        <div class="species-wrap">
          <span
            v-for="s in speciesList"
            :key="s"
            class="species"
            :class="{ on: items[method].species.includes(s) }"
            @click="toggleSpecies(method, s)"
          >{{ s }}</span>
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

const sortSpecies = (list) => SPECIES_LIST.filter((s) => (list || []).includes(s))

const emptyItems = () => Object.fromEntries(
  METHOD_LIST.map((m) => [m, { on: false, species: [...DEFAULT_SPECIES], plate: '' }]),
)

const formatEntry = ({ method, species }) => {
  return `${method}${sortSpecies(species).join('')}`
}

export default {
  name: 'AssayMethodEditor',
  components: { ArrowDown, ElIcon, ElPopover },
  props: {
    config: { type: Object, default: null },
    display: { type: String, default: '' },
  },
  emits: ['update:config', 'update:display'],
  data() {
    return {
      methodList: METHOD_LIST,
      speciesList: SPECIES_LIST,
      open: false,
      triggerWidth: 300,
      items: emptyItems(),
      touched: false,
    }
  },
  watch: {
    config: {
      immediate: true,
      deep: true,
      handler() {
        if (!this.open) this.loadConfig()
      },
    },
  },
  mounted() {
    this.$nextTick(() => {
      if (this.$refs.trigger) this.triggerWidth = this.$refs.trigger.offsetWidth
    })
  },
  methods: {
    loadConfig() {
      this.items = emptyItems()
      this.touched = !!(this.config?.entries?.length)
      for (const entry of this.config?.entries || []) {
        if (!this.items[entry.method]) continue
        this.items[entry.method] = {
          on: true,
          species: sortSpecies(entry.species),
          plate: entry.plate_count != null ? String(entry.plate_count) : '',
        }
      }
    },
    toggle(method) {
      const item = this.items[method]
      item.on = !item.on
      if (item.on && !item.species.length) item.species = [...DEFAULT_SPECIES]
      this.commit()
    },
    toggleSpecies(method, species) {
      const item = this.items[method]
      if (!item.on) item.on = true
      const set = new Set(item.species)
      set.has(species) ? set.delete(species) : set.add(species)
      item.species = sortSpecies([...set])
      this.commit()
    },
    setPlate(method, value) {
      const item = this.items[method]
      if (!item.on) item.on = true
      item.plate = value
      this.commit()
    },
    commit() {
      const entries = METHOD_LIST.filter((m) => this.items[m].on).map((m) => {
        const { species, plate } = this.items[m]
        const trimmed = String(plate || '').trim()
        const plateNum = trimmed ? Number(trimmed) : null
        return {
          method: m,
          species: sortSpecies(species),
          plate_count: plateNum != null && !Number.isNaN(plateNum) ? plateNum : null,
        }
      })
      const config = entries.length ? { entries } : null
      this.$emit('update:config', config)
      if (config) {
        this.touched = true
        this.$emit('update:display', entries.map(formatEntry).join(' + '))
      } else if (this.touched) {
        this.$emit('update:display', '')
      }
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
