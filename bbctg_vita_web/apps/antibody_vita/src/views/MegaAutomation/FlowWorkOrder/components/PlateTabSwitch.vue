<template>
  <div class="plate-switch">
    <button
      type="button"
      class="plate-nav"
      :disabled="!nav.left"
      @click="scroll(-1)"
    >
      <el-icon><ArrowLeft /></el-icon>
    </button>
    <div ref="scrollEl" class="plate-switch-scroll" @scroll="updateNav">
      <el-radio-group
        :model-value="modelValue"
        size="small"
        class="plate-radio"
        @update:model-value="$emit('update:modelValue', $event)"
      >
        <el-radio-button
          v-for="index in count"
          :key="prefix + '-' + index"
          :label="String(index - 1)"
        >{{ prefix }}-{{ index }}</el-radio-button>
      </el-radio-group>
    </div>
    <button
      type="button"
      class="plate-nav"
      :disabled="!nav.right"
      @click="scroll(1)"
    >
      <el-icon><ArrowRight /></el-icon>
    </button>
  </div>
</template>

<script>
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue';
import { ElIcon, ElRadioButton, ElRadioGroup } from 'element-plus';

export default {
  name: 'PlateTabSwitch',
  components: {
    ArrowLeft,
    ArrowRight,
    ElIcon,
    ElRadioButton,
    ElRadioGroup,
  },
  props: {
    modelValue: {
      type: String,
      default: '0',
    },
    count: {
      type: Number,
      default: 0,
    },
    prefix: {
      type: String,
      required: true,
    },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      nav: { left: false, right: false },
    };
  },
  watch: {
    count() {
      this.scheduleLayout();
    },
    modelValue() {
      this.scrollSelectedIntoView();
    },
  },
  mounted() {
    this.scheduleLayout();
    window.addEventListener('resize', this.scheduleLayout);
  },
  activated() {
    window.addEventListener('resize', this.scheduleLayout);
    this.scheduleLayout();
  },
  deactivated() {
    window.removeEventListener('resize', this.scheduleLayout);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.scheduleLayout);
  },
  methods: {
    scheduleLayout() {
      this.$nextTick(() => {
        this.updateNav();
        this.scrollSelectedIntoView();
      });
    },
    scrollSelectedIntoView() {
      this.$nextTick(() => {
        const el = this.$refs.scrollEl;
        if (!el) return;
        const idx = Number(this.modelValue);
        if (Number.isNaN(idx)) return;
        const buttons = el.querySelectorAll('.el-radio-button');
        const target = buttons[idx];
        if (!target) return;
        const left = target.offsetLeft;
        const right = left + target.offsetWidth;
        if (left < el.scrollLeft) {
          el.scrollLeft = left;
        } else if (right > el.scrollLeft + el.clientWidth) {
          el.scrollLeft = right - el.clientWidth;
        }
        this.updateNav();
      });
    },
    scroll(dir) {
      const el = this.$refs.scrollEl;
      if (!el) return;
      el.scrollBy({ left: dir * el.clientWidth, behavior: 'smooth' });
    },
    updateNav() {
      const el = this.$refs.scrollEl;
      if (!el) return;
      this.nav.left = el.scrollLeft > 1;
      this.nav.right = Math.ceil(el.scrollLeft + el.clientWidth) < el.scrollWidth - 1;
    },
  },
};
</script>

<style scoped lang="scss">
$primary: #409eff;
$label-color: #606266;
$border-color: #e4e7ed;

.plate-switch {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 1 auto;
  width: max-content;
  min-width: 0;
  max-width: 513px;
  margin-left: auto;
}

.plate-nav {
  flex: none;
  width: 22px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid $border-color;
  border-radius: 4px;
  background: #fff;
  color: $label-color;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;

  .el-icon {
    font-size: 12px;
  }

  &:hover:not(:disabled) {
    color: $primary;
    border-color: $primary;
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.plate-switch-scroll {
  flex: 0 1 auto;
  width: max-content;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  border: 1px solid $border-color;
  border-radius: 4px;
  scrollbar-width: none;
  scroll-snap-type: x mandatory;

  &::-webkit-scrollbar {
    display: none;
  }
}

.plate-radio {
  display: inline-flex;
  flex-wrap: nowrap;
  vertical-align: top;

  :deep(.el-radio-button) {
    scroll-snap-align: start;
  }

  :deep(.el-radio-button__inner) {
    width: 76px;
    padding-left: 0;
    padding-right: 0;
    text-align: center;
    white-space: nowrap;
    border: none;
    border-right: 1px solid $border-color;
    border-radius: 0;
    box-shadow: none !important;
    outline: none;
  }

  :deep(.el-radio-button:last-child .el-radio-button__inner) {
    border-right: none;
  }

  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    border-color: transparent;
    box-shadow: none !important;
  }
}
</style>
