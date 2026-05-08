<template>
  <div class="plate-card">
    <div class="plate-content">
      <div class="top-row">
        <div class="left-top-panel">
          <div class="form-section">
            <div class="section-header">
              <div class="header-left">
                <el-icon><FolderOpened /></el-icon>
                <span>文件选择</span>
              </div>
            </div>
            <el-form label-width="80px" class="plate-form">
              <el-form-item label="96孔板图片">
                <el-select
                  v-model="plateData.image_file_id"
                  placeholder="请从上方文件列表中选择"
                  filterable
                  clearable
                  :disabled="!isEditable"
                  style="width: 100%"
                  @change="autoSave"
                  @clear="onClearFile('image')"
                >
                  <el-option
                    v-for="file in imageFileOptions"
                    :key="file.id"
                    :label="file.file_name"
                    :value="file.id"
                  >
                    <span style="float: left">{{ file.file_name }}</span>
                    <span style="float: right; color: #8492a6; font-size: 13px">{{ file.created_time }}</span>
                  </el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="Excel结果">
                <el-select
                  v-model="plateData.excel_file_id"
                  placeholder="请从上方文件列表中选择"
                  filterable
                  clearable
                  :disabled="!isEditable"
                  style="width: 100%"
                  @change="autoSave"
                  @clear="onClearFile('excel')"
                >
                  <el-option
                    v-for="file in excelFileOptions"
                    :key="file.id"
                    :label="file.file_name"
                    :value="file.id"
                  >
                    <span style="float: left">{{ file.file_name }}</span>
                    <span style="float: right; color: #8492a6; font-size: 13px">{{ file.created_time }}</span>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <div class="form-section basic-info-section">
            <div class="section-header">
              <div class="header-left">
                <el-icon><EditPen /></el-icon>
                <span>基本信息</span>
              </div>
              <div v-if="isSaving" class="header-right">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>保存中...</span>
              </div>
            </div>
            <el-form label-width="80px" class="plate-form">
              <el-form-item label="二维码编号">
                <el-input v-model="plateData.qr_code" placeholder="扫描或输入二维码" :disabled="!isEditable" @change="autoSave" />
              </el-form-item>
              <el-form-item label="免疫阶段">
                <el-select v-model="plateData.immune_stage" placeholder="请选择免疫阶段" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('immune_stage')">
                  <el-option
                    v-for="stage in immuneStageOptions"
                    :key="stage"
                    :label="stage"
                    :value="stage"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="细胞标靶">
                <el-select v-model="plateData.cell_target_id" placeholder="请选择细胞标靶" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('cell_target_id')">
                  <el-option
                    v-for="target in targetOptions"
                    :key="target.id"
                    :label="target.name"
                    :value="target.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="横坐标参数">
                <el-input v-model="plateData.x_axis" placeholder="如：SSC-H" :disabled="!isEditable" @change="autoSave" />
              </el-form-item>
              <el-form-item label="纵坐标参数">
                <el-input v-model="plateData.y_axis" placeholder="如：RL1-H" :disabled="!isEditable" @change="autoSave" />
              </el-form-item>
              <el-form-item label="上半PC">
                <el-select v-model="plateData.pc_upper_id" placeholder="请选择上PC" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('pc_upper_id')">
                  <el-option
                    v-for="pc in pcOptions"
                    :key="pc.id"
                    :label="pc.pc_name"
                    :value="pc.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="下半PC">
                <el-select v-model="plateData.pc_lower_id" placeholder="请选择下PC" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('pc_lower_id')">
                  <el-option
                    v-for="pc in pcOptions"
                    :key="pc.id"
                    :label="pc.pc_name"
                    :value="pc.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="上半组别">
                <el-select v-model="plateData.upper_group" placeholder="请选择上半组别" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('upper_group')">
                  <el-option
                    v-for="group in groupOptions"
                    :key="group"
                    :label="group"
                    :value="group"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="下半组别">
                <el-select v-model="plateData.lower_group" placeholder="请选择下半组别" clearable :disabled="!isEditable" style="width: 100%" @change="autoSave" @clear="onClearFile('lower_group')">
                  <el-option
                    v-for="group in groupOptions"
                    :key="group"
                    :label="group"
                    :value="group"
                  />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="right-panel">
          <div class="image-section">
            <div class="section-title">
              <div class="header-left">
                <el-icon><Picture /></el-icon>
                <span>96孔板图片预览</span>
              </div>
              <div class="header-right">
                <el-button type="text" class="delete-btn" :disabled="!isEditable" @click="handleDelete">
                  <el-icon><Delete /></el-icon>
                  <span>删除此板</span>
                </el-button>
                <el-button type="text" class="mask-toggle-btn" :disabled="!isEditable" @click="handleMaskToggle" @contextmenu.prevent.stop="handleMaskContextMenu">
                  <el-icon><Setting /></el-icon>
                  <span>仪器类型: {{ plateData.instrument_type || '国产' }}</span>
                </el-button>
              </div>
            </div>

            <div class="image-display">
              <div class="wells-row top-wells">
                <div class="well-input">
                  <el-input
                    model-value="NC"
                    disabled
                    size="small"
                  />
                </div>
                <div
                  v-for="i in 10"
                  :key="'top-' + i"
                  class="well-input"
                >
                  <el-input
                    :ref="'top-' + i"
                    :model-value="getUpperWell(i - 1)"
                    size="small"
                    :disabled="!isEditable"
                    @input="setUpperWell(i - 1, $event)"
                    @keydown.enter.prevent="handleWellEnter('top', i)"
                  />
                </div>
                <div class="well-input">
                  <el-input
                    model-value="PC"
                    disabled
                    size="small"
                  />
                </div>
              </div>

              <div class="image-preview-area" ref="imageContainer">
                <div v-if="!selectedImageUrl" class="empty-image">
                  <el-icon><Picture /></el-icon>
                  <p>请先选择图片</p>
                </div>
                <img v-else :src="selectedImageUrl" class="preview-image" ref="previewImage" @load="handleImageLoad">
                <div v-if="selectedImageUrl" class="well-grid-overlay" :style="gridStyle">
                  <div
                    v-for="(row, rowIndex) in 8"
                    :key="'row-' + rowIndex"
                    class="grid-row"
                  >
                    <div
                      v-for="(col, colIndex) in 12"
                      :key="'cell-' + rowIndex + '-' + colIndex"
                      class="grid-cell"
                      :class="{ 'positive': wellMatrix[rowIndex][colIndex] }"
                      @click="toggleWellStatus(rowIndex, colIndex)"
                    >
                      <span class="cell-label">{{ String.fromCharCode(65 + rowIndex) }}{{ colIndex + 1 }}</span>
                      <el-icon v-if="wellMatrix[rowIndex][colIndex]" class="check-icon"><Check /></el-icon>
                    </div>
                  </div>
                </div>

                <div v-if="showMaskAdjuster" class="mask-adjuster">
                  <div class="adjuster-header">
                    <el-icon><Setting /></el-icon>
                    <span>遮罩调节器</span>
                  </div>
                  <div class="adjuster-content">
                    <div class="adjuster-row">
                        <span>上:</span>
                        <el-input-number v-model="maskOffset.top" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                        <span>下:</span>
                        <el-input-number v-model="maskOffset.bottom" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                      </div>
                      <div class="adjuster-row">
                        <span>左:</span>
                        <el-input-number v-model="maskOffset.left" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                        <span>右:</span>
                        <el-input-number v-model="maskOffset.right" :min="0" :max="50" :step="0.1" size="small" controls-position="right" :disabled="!isEditable" @change="updateGridBBox(false)" />
                      </div>
                    <div class="adjuster-presets">
                      <span class="preset-label">快速选项:</span>
                      <el-button size="small" :disabled="!isEditable" @click="setInstrument('国产')">国产</el-button>
                      <el-button size="small" :disabled="!isEditable" @click="setInstrument('赛多利斯')">赛多利斯</el-button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="wells-row bottom-wells">
                <div class="well-input">
                  <el-input
                    model-value="NC"
                    disabled
                    size="small"
                  />
                </div>
                <div
                  v-for="i in 10"
                  :key="'bottom-' + i"
                  class="well-input"
                >
                  <el-input
                    :ref="'bottom-' + i"
                    :model-value="getLowerWell(i - 1)"
                    size="small"
                    :disabled="!isEditable"
                    @input="setLowerWell(i - 1, $event)"
                    @keydown.enter.prevent="handleWellEnter('bottom', i)"
                  />
                </div>
                <div class="well-input">
                  <el-input
                    model-value="PC"
                    disabled
                    size="small"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {
  Check,
  Delete,
  EditPen,
  FolderOpened,
  Loading,
  Picture,
  Setting,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElMessageBox,
  ElOption,
  ElSelect,
} from 'element-plus'

const GATE_TEMPLATES = {
  domestic: { top: 7.3, left: 3.9, bottom: 4.4, right: 2.1 },
  cytomics: { top: 9.5, left: 6.6, bottom: 5.2, right: 3.6 }
}
const serumApiBaseUrl = import.meta.env.VITE_SERUM_API_URL || '/serum-api'

export default {
  name: 'FacsPlateCard',
  components: {
    Check,
    Delete,
    EditPen,
    ElButton,
    ElForm,
    ElFormItem,
    ElIcon,
    ElInput,
    ElInputNumber,
    ElOption,
    ElSelect,
    FolderOpened,
    Loading,
    Picture,
    Setting,
  },
  props: {
    plateData: {
      type: Object,
      default: () => ({
        id: null,
        experiment_id: '',
        qr_code: '',
        image_file_id: null,
        excel_file_id: null,
        immune_stage: '',
        x_axis: '',
        y_axis: '',
        cell_target_id: null,
        pc_upper_id: null,
        pc_lower_id: null,
        upper_group: '',
        lower_group: '',
        upper_mouse_list: [],
        lower_mouse_list: [],
        positive_well_list: [],
        instrument_type: '国产',
        tempId: null
      })
    },
    targetOptions: {
      type: Array,
      default: () => []
    },
    pcOptions: {
      type: Array,
      default: () => []
    },
    fileList: {
      type: Array,
      default: () => []
    },
    immuneStageOptions: {
      type: Array,
      default: () => []
    },
    groupOptions: {
      type: Array,
      default: () => []
    },
    isActive: {
      type: Boolean,
      default: false
    },
    isSaving: {
      type: Boolean,
      default: false
    },
    isEditable: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      imageNaturalSize: { width: 0, height: 0 },
      gridBBox: { x: 0, y: 0, width: 0, height: 0 },
      containRect: { dx: 0, dy: 0, scale: 1, dw: 0, dh: 0 },
      wellMatrix: Array(8).fill(null).map(() => Array(12).fill(false)),
      showMaskAdjuster: false,
      maskOffset: {
        top: 7.5,
        right: 2,
        bottom: 4,
        left: 4.1
      },
      saveTimer: null
    }
  },
  computed: {
    imageFileOptions() {
      return this.fileList.filter(file => this.isImage(file.file_name))
    },
    excelFileOptions() {
      return this.fileList.filter(file => this.isExcel(file.file_name))
    },
    selectedImageFile() {
      if (!this.plateData.image_file_id) return null
      return this.fileList.find(f => f.id === this.plateData.image_file_id)
    },
    selectedImageUrl() {
      if (!this.selectedImageFile) return ''
      return this.getImageUrl(this.selectedImageFile)
    },
    gridStyle() {
      const { dx, dy, scale } = this.containRect
      const { x, y, width, height } = this.gridBBox
      
      if (!width || !height || !scale) {
        return { display: 'none' }
      }
      
      return {
        position: 'absolute',
        left: `${dx + x * scale}px`,
        top: `${dy + y * scale}px`,
        width: `${width * scale}px`,
        height: `${height * scale}px`
      }
    }
  },
  watch: {
    'plateData.positive_well_list': {
      handler(newVal) {
        if (Array.isArray(newVal)) {
          const wellLabels = newVal.filter(w => w && typeof w === 'string')
          this.initWellMatrix(wellLabels)
        } else {
          this.wellMatrix = Array(8).fill(null).map(() => Array(12).fill(false))
        }
      },
      immediate: true
    },
    'plateData.instrument_type': {
      handler(newVal) {
        const type = newVal === '赛多利斯' ? 'cytomics' : 'domestic'
        this.applyPreset(type, false)
      },
      immediate: true
    },
    isActive(val) {
      if (val) this.forceRecalc()
    },
    selectedImageUrl() {
      this.imageNaturalSize = { width: 0, height: 0 }
      this.forceRecalc()
    }
  },
  methods: {
    isImage(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)
    },
    isExcel(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      return ['xls', 'xlsx', 'csv'].includes(ext)
    },
    getImageUrl(file) {
      const baseUrl = serumApiBaseUrl
      return `${baseUrl}/serum/titer/file/download?id=${file.id}&preview=true`
    },
    autoSave() {
      if (!this.isEditable) return
      if (this.saveTimer) clearTimeout(this.saveTimer)
      this.saveTimer = setTimeout(() => {
        this.ensureWellArrays()
        const toNullIfEmpty = (v) => (v === '' || v === undefined ? null : v)
        const payload = {
          ...this.plateData,
          image_file_id: toNullIfEmpty(this.plateData.image_file_id),
          excel_file_id: toNullIfEmpty(this.plateData.excel_file_id),
          immune_stage: this.plateData.immune_stage === null ? '' : this.plateData.immune_stage,
          cell_target_id: toNullIfEmpty(this.plateData.cell_target_id),
          pc_upper_id: toNullIfEmpty(this.plateData.pc_upper_id),
          pc_lower_id: toNullIfEmpty(this.plateData.pc_lower_id),
          upper_group: this.plateData.upper_group === null ? '' : this.plateData.upper_group,
          lower_group: this.plateData.lower_group === null ? '' : this.plateData.lower_group
        }
        this.$emit('save', payload)
      }, 200)
    },
    onClearFile(type) {
      if (!this.isEditable) return
      if (type === 'image') this.plateData.image_file_id = null
      if (type === 'excel') this.plateData.excel_file_id = null
      if (type === 'immune_stage') this.plateData.immune_stage = null
      if (type === 'cell_target_id') this.plateData.cell_target_id = null
      if (type === 'pc_upper_id') this.plateData.pc_upper_id = null
      if (type === 'pc_lower_id') this.plateData.pc_lower_id = null
      if (type === 'upper_group') this.plateData.upper_group = null
      if (type === 'lower_group') this.plateData.lower_group = null
      this.autoSave()
    },
    ensureWellArrays() {
      if (!Array.isArray(this.plateData.upper_mouse_list)) {
        this.plateData.upper_mouse_list = Array(10).fill('')
      }
      if (!Array.isArray(this.plateData.lower_mouse_list)) {
        this.plateData.lower_mouse_list = Array(10).fill('')
      }
      
      while (this.plateData.upper_mouse_list.length < 10) this.plateData.upper_mouse_list.push('')
      while (this.plateData.lower_mouse_list.length < 10) this.plateData.lower_mouse_list.push('')
      
      this.plateData.upper_mouse_list = this.plateData.upper_mouse_list.slice(0, 10)
      this.plateData.lower_mouse_list = this.plateData.lower_mouse_list.slice(0, 10)
    },
    getUpperWell(idx) {
      return Array.isArray(this.plateData.upper_mouse_list)
        ? (this.plateData.upper_mouse_list[idx] || '')
        : ''
    },
    getLowerWell(idx) {
      return Array.isArray(this.plateData.lower_mouse_list)
        ? (this.plateData.lower_mouse_list[idx] || '')
        : ''
    },
    setUpperWell(idx, val) {
      if (!this.isEditable) return
      const v = (val && val.target) ? val.target.value : val
      this.ensureWellArrays()
      this.plateData.upper_mouse_list[idx] = v
      this.autoSave()
    },
    setLowerWell(idx, val) {
      if (!this.isEditable) return
      const v = (val && val.target) ? val.target.value : val
      this.ensureWellArrays()
      this.plateData.lower_mouse_list[idx] = v
      this.autoSave()
    },
    handleWellEnter(row, index) {
      const nextIndex = index + 1
      if (nextIndex > 10) return
      
      const nextRef = `${row}-${nextIndex}`
      let ref = this.$refs[nextRef]
      
      if (Array.isArray(ref)) ref = ref[0]
      if (!ref) return
      
      if (typeof ref.focus === 'function') {
        ref.focus()
        return
      }
      
      const el = ref.$el ? ref.$el.querySelector('input') : null
      if (el) el.focus()
    },
    calcGridBBoxByMarginPct(iw, ih, { top, left, bottom, right }) {
      const x0 = iw * (left / 100)
      const y0 = ih * (top / 100)
      const w0 = iw * (1 - (left + right) / 100)
      const h0 = ih * (1 - (top + bottom) / 100)
      return { x: x0, y: y0, width: w0, height: h0 }
    },
    calcContainRect(cw, ch, iw, ih) {
      const scale = Math.min(cw / iw, ch / ih)
      const dw = iw * scale
      const dh = ih * scale
      const dx = (cw - dw) / 2
      const dy = (ch - dh) / 2
      return { dx, dy, scale, dw, dh }
    },
    handleImageLoad(event) {
      const img = event.target
      this.imageNaturalSize = { width: img.naturalWidth, height: img.naturalHeight }
      
      this.updateGridBBox(false)
      this.forceRecalc()
    },
    updateGridBBox(shouldSave = true) {
      if (!this.isEditable && shouldSave) return
      if (!this.imageNaturalSize.width) return
      
      const { width: iw, height: ih } = this.imageNaturalSize
      const { top, left, bottom, right } = this.maskOffset
      this.gridBBox = this.calcGridBBoxByMarginPct(iw, ih, { top, left, bottom, right })
      if (shouldSave) {
        this.autoSave()
      }
    },
    applyPreset(type, shouldSave = false) {
      const tpl = GATE_TEMPLATES[type]
      if (!tpl) return
      
      this.maskOffset = { ...tpl }
      if (this.imageNaturalSize.width) {
        this.updateGridBBox(shouldSave)
      }
    },
    setInstrument(label) {
      if (!this.isEditable) return
      this.plateData.instrument_type = label
      const type = label === '赛多利斯' ? 'cytomics' : 'domestic'
      this.applyPreset(type, true)
    },
    forceRecalc() {
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          this.recalcOverlay()
          requestAnimationFrame(() => this.recalcOverlay())
        })
      })
    },
    recalcOverlay() {
      this.$nextTick(() => {
        const container = this.$refs.imageContainer
        const img = this.$refs.previewImage
        const { width: iw, height: ih } = this.imageNaturalSize
        
        if (!container || !img || !iw || !ih) return
        
        const c = container.getBoundingClientRect()
        const r = img.getBoundingClientRect()
        
        const dx = r.left - c.left
        const dy = r.top - c.top
        const scale = r.width / iw
        
        this.containRect = { dx, dy, scale, dw: r.width, dh: r.height }
      })
    },
    toggleWellStatus(rowIndex, colIndex) {
      if (!this.isEditable) return
      this.wellMatrix[rowIndex][colIndex] = !this.wellMatrix[rowIndex][colIndex]
      
      const wellCode = `${String.fromCharCode(65 + rowIndex)}${colIndex + 1}`
      const currentList = Array.isArray(this.plateData.positive_well_list) 
        ? [...this.plateData.positive_well_list] 
        : []
      
      if (this.wellMatrix[rowIndex][colIndex]) {
        if (!currentList.includes(wellCode)) {
          currentList.push(wellCode)
        }
      } else {
        const index = currentList.indexOf(wellCode)
        if (index !== -1) {
          currentList.splice(index, 1)
        }
      }
      
      this.plateData.positive_well_list = currentList
      this.autoSave()
    },
    handleMaskToggle() {
      if (!this.isEditable) return
      if (this.plateData.instrument_type === '国产') {
        this.plateData.instrument_type = '赛多利斯'
      } else {
        this.plateData.instrument_type = '国产'
      }
      this.autoSave()
    },
    handleMaskContextMenu() {
      if (!this.isEditable) return
      this.showMaskAdjuster = !this.showMaskAdjuster
    },
    handleDelete() {
      if (!this.isEditable) return
      ElMessageBox.confirm('确定要删除这个FACS板吗？', '提示', {
        type: 'warning'
      }).then(() => {
        this.$emit('delete', this.plateData)
      }).catch(() => {})
    },
    getPlateData() {
      return this.plateData
    },
    initWellMatrix(wells) {
      const matrix = Array(8).fill(null).map(() => Array(12).fill(false))
      wells.forEach(well => {
        const match = well.match(/^([A-H])(\d+)$/)
        if (match) {
          const row = match[1].charCodeAt(0) - 65
          const col = parseInt(match[2]) - 1
          if (row >= 0 && row < 8 && col >= 0 && col < 12) {
            matrix[row][col] = true
          }
        }
      })
      this.wellMatrix = matrix
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.ensureWellArrays()
      
      const el = this.$refs.imageContainer
      if (el && window.ResizeObserver) {
        this._ro = new ResizeObserver(() => this.recalcOverlay())
        this._ro.observe(el)
      }
      if (this.isActive) this.forceRecalc()
      
      const type = this.plateData.instrument_type === '赛多利斯' ? 'cytomics' : 'domestic'
      this.applyPreset(type)
    })
  },
  beforeUnmount() {
    if (this._ro) this._ro.disconnect()
    if (this.saveTimer) clearTimeout(this.saveTimer)
  }
}
</script>

<style lang="scss" scoped>
.plate-card {
  .plate-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px 0 20px 20px;
  }
}

/* Component-local small size semantics */
.plate-card :deep(.el-button--small) {
  height: 28px;
  padding: 7px 15px;
  font-size: 12px;
  border-radius: 3px;
}

.plate-card :deep(.el-input--small),
.plate-card :deep(.el-select--small) {
  --el-input-height: 28px;
  font-size: 12px;
}

.plate-card :deep(.el-input--small .el-input__wrapper),
.plate-card :deep(.el-select--small .el-select__wrapper) {
  min-height: 28px;
  font-size: 12px;
}

.plate-card :deep(.el-input-number--small) {
  line-height: 26px;
  font-size: 12px;
}

.plate-card :deep(.el-input-number--small .el-input-number__decrease),
.plate-card :deep(.el-input-number--small .el-input-number__increase) {
  width: 28px;
  font-size: 12px;
}

.top-row {
  display: flex;
  gap: 20px;
  align-items: stretch;
}

.left-top-panel {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;

  .form-section {
    &:first-child {
      flex-shrink: 0;
    }

    &:last-child {
      flex: 1;
      display: flex;
      flex-direction: column;

      .plate-form {
        flex: 1;
        display: flex;
        flex-direction: column;
      }
    }
  }
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;

  .image-section {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #303133;
    margin-bottom: 8px;
    padding: 0 10px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .el-icon {
      color: #409EFF;
      font-size: 14px;
    }

    .delete-btn {
      color: #F56C6C;
      height: auto;
      font-size: 14px;
      line-height: 1;
      padding: 0 4px;
    }

    .mask-toggle-btn {
      color: #409EFF;
      height: auto;
      font-size: 14px;
      line-height: 1;
      padding: 0 4px;
    }

    .delete-btn .el-icon,
    .mask-toggle-btn .el-icon {
      color: inherit;
    }
  }

  .image-display {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
    background: #fafafa;
    border-radius: 8px;
    padding: 20px;
    min-height: 0;
  }

  .wells-row {
    display: flex;
    gap: 8px;
    width: 100%;
    justify-content: center;
    flex-shrink: 0;

    .well-input {
      width: 60px;
      flex-shrink: 0;
    }
  }

  .image-preview-area {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    border-radius: 8px;
    border: 2px dashed #e4e7ed;
    position: relative;
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
    min-height: 450px;

    .empty-image {
      text-align: center;
      color: #c0c4cc;

      .el-icon {
        font-size: 64px;
        margin-bottom: 16px;
      }

      p {
        margin: 0;
        font-size: 14px;
      }
    }

    .preview-image {
      max-width: 100%;
      width: 100%;
      height: auto;
      object-fit: contain;
      display: block;
    }

    .well-grid-overlay {
      position: absolute;
      display: flex;
      flex-direction: column;
      pointer-events: auto;
      z-index: 10;
    }

    .mask-adjuster {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.95);
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
      z-index: 20;
      min-width: 200px;

      .adjuster-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #ebeef5;

        .el-icon {
          color: #409EFF;
        }
      }

      .adjuster-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .adjuster-row {
        display: flex;
        align-items: center;
        gap: 8px;

        span {
          font-size: 12px;
          color: #606266;
          min-width: 24px;
        }

        :deep(.el-input-number) {
          flex: 1;
          width: auto;

          .el-input__wrapper {
            padding-left: 8px;
            padding-right: 8px;
          }

          .el-input__inner {
            padding-left: 8px;
            padding-right: 8px;
          }
        }
      }

      .adjuster-presets {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #ebeef5;

        .preset-label {
          font-size: 12px;
          color: #606266;
          min-width: 60px;
        }
      }
    }

    .grid-row {
      display: flex;
      flex: 1;
    }

    .grid-cell {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      border: 1px solid rgba(255, 255, 255, 0.5);
      background: rgba(0, 0, 0, 0);
      transition: all 0.2s ease;

      &:hover {
        background: rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.7);
      }

      .cell-label {
        position: absolute;
        top: 2px;
        left: 4px;
        font-size: 10px;
        color: rgb(255, 255, 255);
        font-weight: 500;
        text-shadow: 0 1px 2px rgb(0, 0, 0);
      }

      .check-icon {
        position: absolute;
        top: 2px;
        right: 2px;
        color: #f03b3b;
        font-size: 16px;
        font-weight: bold;
        text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
      }

      &.positive {
        background: rgba(100, 200, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.6);

        &:hover {
          background: rgba(100, 200, 255, 0.5);
        }
      }
    }
  }
}

.bottom-row {
  display: flex;
  gap: 16px;

  .form-section {
    flex: 1;
  }
}

.form-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #303133;
    margin-bottom: 2px;
    padding-bottom: 12px;
    border-bottom: 1px solid #ebeef5;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #909399;

      .el-icon {
        font-size: 14px;
      }
    }

    .el-icon {
      color: #409EFF;
      font-size: 14px;
    }

    .delete-btn {
      color: #F56C6C;
    }

    &:has(.delete-btn) {
      justify-content: space-between;
    }
  }

  .plate-form {
    flex: 1;
    display: flex;
    flex-direction: column;

    :deep(.el-form-item) {
      margin-bottom: 10px;
      display: flex;
      align-items: flex-start;

      .el-form-item__label {
        text-align: left;
        justify-content: flex-start;
        padding-right: 8px;
        font-size: 14px;
        font-weight: 700;
        line-height: 32px;
        color: #606266;
      }

      .el-form-item__content {
        flex: 1;
        display: flex;
        margin-left: 75px !important;

        .el-input,
        .el-select {
          font-size: 14px;
        }

        .el-input,
        .el-select,
        .el-textarea__inner {
          width: 100%;
        }
      }
    }
  }
}
</style>
