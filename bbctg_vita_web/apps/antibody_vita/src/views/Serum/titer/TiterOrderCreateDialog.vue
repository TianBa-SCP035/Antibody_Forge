<template>
  <el-dialog
    :model-value="modelValue"
    class="titer-order-create-dialog"
    :title="dialogTitle"
    width="760px"
    append-to-body
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="handleOpen"
    @closed="resetForm"
  >
    <div class="create-dialog-body">
      <el-form label-width="108px" class="create-form">
        <el-form-item class="experiment-form-item">
          <template #label>
            <span class="field-label-tag">
              <span class="field-label-icon" aria-hidden="true">🔍</span>
              免疫实验
            </span>
          </template>
          <el-select
            v-model="experimentId"
            filterable
            remote
            reserve-keyword
            :remote-method="fetchProjectOptions"
            :loading="projectLoading"
            :disabled="isEditMode"
            placeholder="项目编号 / 实验ID / 靶点"
            popper-class="titer-create-select-dropdown"
            style="width: 100%"
            @change="handleExperimentChange"
          >
            <el-option
              v-for="project in projectOptions"
              :key="project.experiment_id"
              :label="projectOptionLabel(project)"
              :value="project.experiment_id"
            >
              <div class="project-option">
                <span class="project-option-main">
                  {{ project.project_code || '-' }} / {{ project.experiment_id }}
                </span>
                <span class="project-option-target">{{ project.target_name || '-' }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="selectedProject" class="selected-project-card">
        <div class="selected-project-code">{{ selectedProject.project_code || '-' }}</div>
        <div class="selected-project-meta text-hint">
          实验ID：{{ selectedProject.experiment_id }}　靶点：{{ selectedProject.target_name || '-' }}
        </div>
      </div>

      <template v-if="experimentId">
        <p class="batch-hint text-hint">{{ batchHint }}</p>
        <div v-loading="batchPreviewLoading" class="batch-table-wrap" :class="{ 'batch-table-readonly': isBatchReadonly }">
          <el-table
            :data="[batchForm]"
            border
            size="small"
            class="batch-table"
            style="width: 100%"
          >
            <el-table-column label="检测方法" min-width="240" align="center" class-name="assay-method-col">
              <template #default>
                <AssayMethodEditor
                  v-model:assay-method="batchForm.assay_method"
                  v-model:facs-plate-count="batchForm.facs_plate_count"
                  v-model:elisa-plate-count="batchForm.elisa_plate_count"
                  class="assay-editor-compact"
                />
              </template>
            </el-table-column>
            <el-table-column label="FACS" min-width="60" align="center">
              <template #default>
                <el-input-number
                  :model-value="facsPlateCount"
                  :min="0"
                  :controls="false"
                  size="small"
                  @update:model-value="updatePlateCount('FACS', $event)"
                />
              </template>
            </el-table-column>
            <el-table-column label="ELISA" min-width="60" align="center">
              <template #default>
                <el-input-number
                  :model-value="elisaPlateCount"
                  :min="0"
                  :controls="false"
                  size="small"
                  @update:model-value="updatePlateCount('ELISA', $event)"
                />
              </template>
            </el-table-column>
            <el-table-column label="笼位" min-width="100" align="center">
              <template #default="{ row }">
                <el-input v-model="row.cage_position" size="small" clearable />
              </template>
            </el-table-column>
            <el-table-column label="采血日期" min-width="110" align="center">
              <template #default="{ row }">
                <el-date-picker
                  v-model="row.blood_collection_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="日期"
                  clearable
                  size="small"
                />
              </template>
            </el-table-column>
            <el-table-column label="只数" min-width="60" align="center">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.mouse_count"
                  :min="0"
                  :controls="false"
                  size="small"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>

    <template #footer>
      <div class="dialog-footer-inner">
        <el-button
          v-if="isEditMode && canDelete"
          type="danger"
          plain
          :loading="deleteLoading"
          @click="confirmDelete"
        >
          删除实验
        </el-button>
        <div class="footer-main-actions">
          <el-button @click="closeDialog">取消</el-button>
          <el-button
            type="primary"
            :loading="submitLoading"
            :disabled="!canSubmit"
            @click="submit"
          >
            {{ isEditMode ? '保存' : '创建' }}
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus';

import { notifyApiError } from '#/api/errors';
import {
  deleteTiterOrder,
  fetchTiterOrderBatchPreview,
  fetchTiterOrderProjectOptions,
  saveTiterOrder,
} from '#/api/serum';

import AssayMethodEditor from '../shared/AssayMethodEditor.vue';

function emptyBatchForm() {
  return {
    cage_position: '',
    blood_collection_date: '',
    mouse_count: null,
    assay_method: '',
    facs_plate_count: null,
    elisa_plate_count: null,
  };
}

export default {
  name: 'TiterOrderCreateDialog',
  components: {
    AssayMethodEditor,
    ElButton,
    ElDatePicker,
    ElDialog,
    ElForm,
    ElFormItem,
    ElInput,
    ElInputNumber,
    ElOption,
    ElSelect,
    ElTable,
    ElTableColumn,
  },
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    editOrder: {
      type: Object,
      default: null,
    },
    canSaveBatch: {
      type: Boolean,
      default: true,
    },
    canDelete: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue', 'changed', 'closed'],
  data() {
    return {
      orderId: null,
      experimentId: '',
      projectLoading: false,
      projectOptions: [],
      selectedProject: null,
      batchPreviewLoading: false,
      batchForm: emptyBatchForm(),
      submitLoading: false,
      deleteLoading: false,
    };
  },
  computed: {
    isEditMode() {
      return this.orderId != null;
    },
    dialogTitle() {
      return this.isEditMode ? '效价实验' : '新增效价实验';
    },
    batchHint() {
      return this.isEditMode
        ? '可修改下列批次信息后保存。'
        : '批次信息默认来自免疫实验，可在下表修改后创建。';
    },
    facsPlateCount() {
      return this.batchForm.facs_plate_count ?? 0;
    },
    elisaPlateCount() {
      return this.batchForm.elisa_plate_count ?? 0;
    },
    isBatchReadonly() {
      return this.isEditMode && !this.canSaveBatch;
    },
    canSubmit() {
      if (!this.experimentId || this.batchPreviewLoading) {
        return false;
      }
      if (this.isEditMode) {
        return this.canSaveBatch;
      }
      return true;
    },
  },
  methods: {
    handleOpen() {
      if (this.editOrder?.id) {
        this.initEditMode(this.editOrder);
        return;
      }
      this.fetchProjectOptions('');
    },
    initEditMode(row) {
      this.orderId = row.id;
      this.experimentId = row.experiment_id || '';
      this.selectedProject = {
        experiment_id: row.experiment_id,
        project_code: row.project_code,
        target_name: row.target_name,
      };
      this.projectOptions = this.experimentId ? [this.selectedProject] : [];
      this.batchForm = {
        cage_position: row.cage_position || '',
        blood_collection_date: row.blood_collection_date || '',
        mouse_count: row.mouse_count ?? null,
        assay_method: row.assay_method || '',
        facs_plate_count: row.facs_plate_count ?? null,
        elisa_plate_count: row.elisa_plate_count ?? null,
      };
      this.batchPreviewLoading = false;
    },
    resetForm() {
      this.orderId = null;
      this.experimentId = '';
      this.projectOptions = [];
      this.selectedProject = null;
      this.batchPreviewLoading = false;
      this.batchForm = emptyBatchForm();
      this.submitLoading = false;
      this.deleteLoading = false;
      this.$emit('closed');
    },
    closeDialog() {
      this.$emit('update:modelValue', false);
    },
    projectOptionLabel(project) {
      return `${project.project_code || '-'} / ${project.experiment_id}`;
    },
    fetchProjectOptions(keyword) {
      this.projectLoading = true;
      fetchTiterOrderProjectOptions({ keyword, limit: 30 })
        .then((response) => {
          this.projectOptions = response.items || [];
        })
        .catch((error) => {
          this.projectOptions = [];
          notifyApiError(error, { messages: { default: '搜索免疫实验失败' } });
        })
        .finally(() => {
          this.projectLoading = false;
        });
    },
    handleExperimentChange(value) {
      if (this.isEditMode) {
        return;
      }
      this.selectedProject = this.projectOptions.find((project) => project.experiment_id === value) || null;
      if (!value) {
        this.batchForm = emptyBatchForm();
        return;
      }
      this.loadBatchPreview(value);
    },
    loadBatchPreview(experimentId) {
      this.batchPreviewLoading = true;
      fetchTiterOrderBatchPreview(experimentId)
        .then((preview) => {
          this.batchForm = {
            cage_position: preview.cage_position || '',
            blood_collection_date: preview.blood_collection_date || '',
            mouse_count: preview.mouse_count ?? null,
            assay_method: preview.assay_method || '',
            facs_plate_count: preview.facs_plate_count ?? null,
            elisa_plate_count: preview.elisa_plate_count ?? null,
          };
          if (!this.selectedProject) {
            this.selectedProject = {
              experiment_id: preview.experiment_id,
              project_code: preview.project_code,
              target_name: preview.target_name,
            };
          }
        })
        .catch((error) => {
          this.batchForm = emptyBatchForm();
          notifyApiError(error, { messages: { default: '加载批次信息失败' } });
        })
        .finally(() => {
          this.batchPreviewLoading = false;
        });
    },
    updatePlateCount(method, value) {
      const plateCount = value == null || value === '' ? null : Math.max(0, Number(value) || 0);
      if (String(method || '').toUpperCase() === 'FACS') {
        this.batchForm.facs_plate_count = plateCount;
      } else {
        this.batchForm.elisa_plate_count = plateCount;
      }
    },
    submit() {
      if (this.isEditMode) {
        this.submitSave();
        return;
      }
      this.submitCreate();
    },
    submitCreate() {
      if (!this.experimentId) {
        ElMessage.warning('请选择免疫实验');
        return;
      }
      this.submitLoading = true;
      saveTiterOrder({
        experiment_id: this.experimentId,
        ...this.batchForm,
        blood_collection_date: this.batchForm.blood_collection_date || null,
      })
        .then(() => {
          ElMessage.success('效价实验已创建');
          this.$emit('changed');
          this.closeDialog();
        })
        .catch((error) => notifyApiError(error, { messages: { default: '创建效价实验失败' } }))
        .finally(() => {
          this.submitLoading = false;
        });
    },
    submitSave() {
      if (!this.orderId) {
        return;
      }
      if (!this.canSaveBatch) {
        ElMessage.warning('您没有权限编辑批次信息');
        return;
      }
      this.submitLoading = true;
      saveTiterOrder({
        id: this.orderId,
        ...this.batchForm,
        blood_collection_date: this.batchForm.blood_collection_date || null,
      })
        .then(() => {
          ElMessage.success('已保存');
          this.$emit('changed');
          this.closeDialog();
        })
        .catch((error) => notifyApiError(error, { messages: { default: '保存效价实验失败' } }))
        .finally(() => {
          this.submitLoading = false;
        });
    },
    confirmDelete() {
      if (!this.orderId) {
        return;
      }
      if (!this.canDelete) {
        ElMessage.warning('您没有权限删除效价工单');
        return;
      }
      const projectCode = this.selectedProject?.project_code || '-';
      ElMessageBox.confirm(
        `删除项目编号 ${projectCode} 的效价工单？删除后不可恢复。`,
        '确认删除',
        {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
        },
      )
        .then(() => {
          this.deleteLoading = true;
          return deleteTiterOrder(this.orderId);
        })
        .then(() => {
          ElMessage.success('效价工单已删除');
          this.$emit('changed');
          this.closeDialog();
        })
        .catch((error) => {
          if (error === 'cancel' || error === 'close') {
            return;
          }
          notifyApiError(error, { messages: { default: '删除效价工单失败' } });
        })
        .finally(() => {
          this.deleteLoading = false;
        });
    },
  },
};
</script>

<style scoped>
.create-dialog-body {
  width: 100%;
}

.create-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.create-form :deep(.experiment-form-item) {
  align-items: center;
}

.create-form :deep(.experiment-form-item .el-form-item__label) {
  display: flex;
  align-items: center;
  height: 32px;
  padding-right: 12px;
  line-height: 1;
}

.field-label-tag {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  font-size: 14px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.field-label-icon {
  font-size: 13px;
  line-height: 1;
}

.selected-project-card {
  margin-bottom: 12px;
  padding: 12px 14px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 4px;
}

.selected-project-code {
  color: var(--el-color-primary);
  font-weight: 700;
}

.selected-project-meta {
  margin-top: 4px;
}

.batch-hint {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.5;
}

.batch-table-wrap {
  width: 100%;
  min-height: 56px;
}

.batch-table {
  --batch-cell-height: 28px;
}

.batch-table :deep(.el-table__body-wrapper),
.batch-table :deep(.el-table__header-wrapper) {
  overflow-x: hidden;
}

.batch-table :deep(.el-table__header th) {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

.batch-table :deep(.cell) {
  padding: 6px 8px;
}

.batch-table :deep(.assay-method-col .cell) {
  overflow: visible;
}

.batch-table :deep(.el-input__wrapper) {
  height: var(--batch-cell-height);
  min-height: var(--batch-cell-height);
  box-sizing: border-box;
}

.batch-table :deep(.el-input__inner) {
  height: 100%;
  font-size: 12px;
}

.batch-table :deep(.el-input-number) {
  width: 100%;
  line-height: var(--batch-cell-height);
}

.batch-table :deep(.el-date-editor) {
  width: 100%;
  height: var(--batch-cell-height);
  vertical-align: middle;
}

.batch-table :deep(.assay-editor-compact .trigger) {
  height: var(--batch-cell-height);
  padding: 0 26px 0 8px;
  font-size: 12px;
}

.batch-table :deep(.assay-editor-compact .trigger .arrow) {
  right: 8px;
}

.dialog-footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 12px;
}

.footer-main-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.text-hint {
  color: #909399;
}

.batch-table-readonly {
  pointer-events: none;
  opacity: 0.72;
}
</style>

<style>
/* 仅在本弹窗打开时加宽检测方法选项（覆盖 el-popover 内联 width） */
body:has(.titer-order-create-dialog) .el-popper:has(.species-wrap) {
  width: 400px !important;
  box-sizing: border-box;
}

.titer-create-select-dropdown .project-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 0;
}

.titer-create-select-dropdown .project-option-main {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-color-primary);
  font-weight: 600;
}

.titer-create-select-dropdown .project-option-target {
  flex-shrink: 0;
  max-width: 42%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #a8abb2;
}
</style>
