<template>
  <div v-loading="loading" class="library-detail">
    <section class="detail-overview">
      <header class="detail-topbar">
        <el-button text class="back-button" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>文库构建</span>
        </el-button>
        <div class="topbar-identity">
          <h1 class="detail-title" :title="pageTitle">{{ pageTitle }}</h1>
          <span class="detail-code" :title="detailSubtitle">{{ detailSubtitle }}</span>
        </div>
        <div class="topbar-state">
          <WorkbenchStatusEditor
            :value="currentStatus"
            :options="statusOptions"
            :type="statusTagType"
            :editable="canEdit"
            @change="updateStatus"
          />
          <WorkbenchStatusEditor
            :value="currentPriority"
            :options="priorityOptions"
            :type="priorityTagType"
            :tag-class="priorityTone === 'king' ? 'status-tone-king' : ''"
            :editable="canEdit"
            @change="updatePriority"
          />
        </div>
        <dl class="topbar-meta">
          <div v-for="item in headerMeta" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd :title="item.value">{{ item.value }}</dd>
          </div>
        </dl>
        <div v-if="qcGaps.length" class="qc-gaps">
          <span v-for="gap in qcGaps" :key="gap.text" :class="gap.tone" :title="gap.title"><i />{{ gap.text }}</span>
        </div>
        <span v-else class="save-hint" :class="{ 'is-readonly': !canEditQc }">
          <i />
          {{ canEditQc ? '自动保存' : '只读' }}
        </span>
      </header>

      <div class="sample-strip">
        <div class="strip-label">
          <strong>样品概览</strong>
        </div>
        <dl class="strip-facts">
          <div v-for="fact in sampleFacts" :key="fact.label" class="strip-fact">
            <dt>{{ fact.label }}</dt>
            <dd :title="fact.value">{{ fact.value }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <main class="review-workspace">
      <aside class="file-rail">
        <header class="rail-heading">
          <strong>结果文件</strong>
          <span class="rail-count">{{ files.length + packages.length }} 个</span>
        </header>
        <div class="file-tile-grid">
          <div
            v-loading="resultUploading"
            class="file-upload-tile"
            :class="{ 'is-disabled': !canManageFiles || resultUploading }"
            role="button"
            tabindex="0"
            @click="pickQcFiles"
            @contextmenu.prevent.stop="pickQcFolder"
            @keydown.enter.prevent="pickQcFiles"
            @keydown.space.prevent="pickQcFiles"
            @dragover.prevent
            @drop.stop.prevent="onDropResults"
          >
            <el-icon><UploadFilled /></el-icon>
            <strong>上传结果文件</strong>
            <span>拖入文件夹或 zip</span>
            <input
              ref="qcFiles"
              class="qc-folder-input"
              type="file"
              multiple
              @click.stop
              @change="onQcFiles"
            />
            <input
              ref="qcFolder"
              class="qc-folder-input"
              type="file"
              webkitdirectory
              multiple
              @click.stop
              @change="onQcFolder"
            />
          </div>
          <button
            v-for="file in files"
            :key="file.id"
            type="button"
            class="file-tile"
            :class="{
              'is-active': file.id === currentFileId,
              'is-final': file.is_final_qc,
              'is-replaced': file.replaced,
            }"
            :title="file.replaced ? `${file.original_name}（同名文件已有最终版本，不参与质检）` : file.original_name"
            @click="selectFile(file)"
          >
            <span class="tile-visual">
              <el-image
                v-if="isImage(file) && file.thumb_object_url"
                :src="file.thumb_object_url"
                fit="cover"
              />
              <span v-else class="tile-file-icon" :class="fileIconClass(file.original_name)">
                <el-icon><component :is="fileIcon(file.original_name)" /></el-icon>
              </span>
              <span
                v-if="showTileExt(file)"
                class="tile-ext-badge"
                :class="fileIconClass(file.original_name)"
              >
                {{ fileExt(file.original_name) }}
              </span>
            </span>
            <span class="tile-name">{{ file.original_name }}</span>
            <small>{{ fileSize(file.byte_size) }}</small>
            <small
              v-if="railSequenceLabel(file)"
              class="tile-check"
              :class="{
                'is-matched': file.sequence_status === 'matched',
                'is-unmatched': file.sequence_status === 'not_found',
              }"
            >
              {{ railSequenceLabel(file) }}
            </small>
            <span v-if="file.is_final_qc" class="tile-final">最终</span>
          </button>
          <button
            v-for="folder in packages"
            :key="folder.id"
            type="button"
            class="file-tile"
            :class="{ 'is-active': selectedPackage && selectedPackage.id === folder.id && !currentFile }"
            @click="selectPackage(folder)"
          >
            <span class="tile-visual">
              <span class="tile-file-icon">
                <el-icon><FolderOpened /></el-icon>
              </span>
            </span>
            <span class="tile-name">{{ folder.name }}</span>
            <small>测序包 · {{ folder.file_count }} 个文件</small>
          </button>
        </div>
      </aside>

      <section ref="viewerPanel" class="viewer-panel" :class="{ 'is-dark': showGelStage, 'is-fullscreen': isFullscreen }">
        <header class="viewer-caption">
          <div class="caption-copy">
            <strong v-if="currentFile" :title="currentFile.original_name">{{ currentFile.original_name }}</strong>
            <strong v-else-if="selectedPackage">{{ selectedPackage.name }}</strong>
            <strong v-else>结果预览</strong>
            <span>{{ currentFile ? fileMeta(currentFile) : selectedPackage ? '测序包里的文件' : '选择文件后在此预览' }}</span>
          </div>
          <div v-if="currentFile || selectedPackage" class="caption-actions">
            <template v-if="currentFile">
            <el-button
              size="small"
              :type="currentFile.is_final_qc ? 'success' : undefined"
              plain
              :disabled="!canManageFiles"
              @click="toggleFinalFile"
            >
              {{ currentFile.is_final_qc ? '已标最终' : '设为最终' }}
            </el-button>
            <el-popover
              v-model:visible="fileRenameOpen"
              placement="bottom"
              trigger="click"
              :width="286"
              :disabled="!canManageFiles"
              @show="prepareFileRename"
              @after-enter="focusFileRenameInput"
            >
              <div class="rename-popover-content">
                <strong>文件改名</strong>
                <el-input
                  ref="fileRenameInput"
                  v-model="fileRenameDraft"
                  maxlength="255"
                  @keydown.enter.prevent="saveFileRename"
                >
                  <template v-if="fileRenameSuffix" #append>{{ fileRenameSuffix }}</template>
                </el-input>
                <small>扩展名保持不变</small>
                <div class="rename-popover-actions">
                  <el-button size="small" @click="closeFileRename">取消</el-button>
                  <el-button size="small" type="primary" @click="saveFileRename">保存</el-button>
                </div>
              </div>
              <template #reference>
                <el-button size="small" :disabled="!canManageFiles">改名</el-button>
              </template>
            </el-popover>
            <el-button size="small" @click="download(currentFile)">
              <el-icon><Download /></el-icon>
              <span>下载</span>
            </el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="!canManageFiles"
              aria-label="删除当前文件"
              title="删除当前文件"
              @click="removeFile(currentFile)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
            </template>
            <el-button
              v-if="selectedPackage"
              size="small"
              type="danger"
              plain
              :disabled="!canManageFiles"
              @click="removePackage(selectedPackage)"
            >
              删除测序包
            </el-button>
          </div>
        </header>

        <div v-if="showGelStage" class="viewer-tools">
          <div class="image-adjustments">
            <label class="tool-slider">
              <span>亮度</span>
              <el-slider
                v-model="view.brightness"
                :min="20"
                :max="320"
                :show-tooltip="false"
                aria-label="亮度"
                size="small"
              />
              <b>{{ view.brightness }}%</b>
            </label>
            <label class="tool-slider">
              <span>对比度</span>
              <el-slider
                v-model="view.contrast"
                :min="20"
                :max="320"
                :show-tooltip="false"
                aria-label="对比度"
                size="small"
              />
              <b>{{ view.contrast }}%</b>
            </label>
          </div>
          <div class="tool-actions">
            <div class="tool-buttons">
              <button type="button" title="反转图像明暗" :class="{ 'is-on': view.invert }" @click="view.invert = !view.invert">
                反相
              </button>
              <button
                type="button"
                :title="isEnhanced ? '恢复默认亮度和对比度' : '提高亮度与对比度'"
                :class="{ 'is-on': isEnhanced }"
                @click="enhance"
              >
                增强
              </button>
              <button
                type="button"
                :class="{ 'is-on': regionDrawing }"
                :disabled="!canManageFiles"
                @click="toggleRegionDrawing"
              >
                {{ regionDrawing ? '取消框选' : currentRegions.length ? '添加区域' : '框选区域' }}
              </button>
              <button
                v-if="currentRegions.length && !regionDrawing"
                type="button"
                :disabled="!canManageFiles"
                @click="clearRegion"
              >
                清除框选
              </button>
            </div>
            <button class="tool-reset" type="button" aria-label="重置图像" title="恢复图像和视图默认状态" @click="resetView">
              <el-icon><RefreshLeft /></el-icon>
            </button>
          </div>
        </div>

        <div
          ref="viewerStage"
          class="viewer-stage"
          :class="{ 'is-grabbing': panning, 'is-selecting': regionDrawing }"
          @wheel="onWheel"
          @mousedown="onStageMouseDown"
        >
          <img
            v-if="showGelStage"
            ref="stageImage"
            class="stage-image"
            :src="gelSource"
            :style="stageStyle"
            draggable="false"
            alt="胶图"
            @load="onStageImageLoad"
          />
          <div v-else-if="selectedPackage && !currentFile" class="stage-package" @mousedown.stop @wheel.stop>
            <header class="package-browser-head">
              <div>
                <strong>{{ selectedPackage.name }}</strong>
                <span>
                  {{ selectedPackage.file_count }} 个文件{{ selectedPackage.qc_count ? ` · 核对 ${selectedPackage.qc_count} 个` : '' }}
                </span>
              </div>
            </header>
            <div class="package-explorer">
              <section class="package-browser-pane">
                <nav class="package-breadcrumb" aria-label="当前文件夹">
                  <button type="button" @click="goPackagePath('')">{{ selectedPackage.name }}</button>
                  <template v-for="crumb in packageBreadcrumbs" :key="crumb.path">
                    <span>/</span>
                    <button type="button" @click="goPackagePath(crumb.path)">{{ crumb.name }}</button>
                  </template>
                </nav>
                <div class="package-list-head">
                  <span>名称</span>
                  <span>类型</span>
                  <span>大小</span>
                  <span>用途</span>
                </div>
                <div class="package-file-list">
                  <button
                    v-for="entry in packageBrowserEntries"
                    :key="entry.key"
                    type="button"
                    class="package-file"
                    :class="{ 'is-active': packageSelectedKey === entry.key }"
                    @click="selectPackageEntry(entry)"
                  >
                    <span class="package-entry-name">
                      <el-icon :class="packageEntryClass(entry)"><component :is="packageEntryIcon(entry)" /></el-icon>
                      <strong>{{ entry.name }}</strong>
                    </span>
                    <span>{{ entry.type === 'folder' ? '文件夹' : fileExt(entry.name) }}</span>
                    <span>{{ entry.type === 'folder' ? `${entry.count} 项` : fileSize(entry.file.byte_size) }}</span>
                    <small>{{ entry.type === 'folder' ? '—' : entry.file.for_qc ? '已关联' : '仅保存' }}</small>
                  </button>
                  <div v-if="!packageBrowserEntries.length" class="package-folder-empty">这个文件夹是空的</div>
                </div>
              </section>

              <aside class="package-preview-pane">
                <div v-if="!packageFocus" class="package-preview-empty">
                  <el-icon><Document /></el-icon>
                  <strong>选择左侧文件预览</strong>
                </div>
                <template v-else>
                  <header class="package-preview-head">
                    <div>
                      <strong>{{ packageFocus.original_name }}</strong>
                      <small>{{ packageDirectory(packageFocus.relative_path) }} · {{ fileSize(packageFocus.byte_size) }}</small>
                      <small v-if="packageFocus.sequence_check">{{ packageFocus.sequence_check }}</small>
                    </div>
                    <div class="package-preview-actions">
                      <el-button size="small" plain @click="downloadStored(packageFocus)">下载</el-button>
                      <el-button
                        size="small"
                        type="danger"
                        plain
                        :disabled="!canManageFiles"
                        aria-label="删除这个文件"
                        title="删除这个文件"
                        @click="deleteStoredFile(packageFocus)"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </div>
                  </header>
                  <AbiTracePreview
                    v-if="isTrace(packageFocus)"
                    :key="`package-${packageFocus.file_id}`"
                    class="package-preview-body"
                    :source-url="storedFilePreviewUrl(packageFocus.file_id)"
                    :direction="traceDirection(packageFocus)"
                    :primer-label="primerLabel(packageFocus)"
                    :target-sequence="traceTargetSequence(packageFocus)"
                    height="100%"
                  />
                  <SeqReadPreview
                    v-else-if="isSequence(packageFocus)"
                    :key="`package-seq-${packageFocus.file_id}`"
                    class="package-preview-body"
                    :source-url="storedFilePreviewUrl(packageFocus.file_id)"
                    :direction="traceDirection(packageFocus)"
                    :primer-label="primerLabel(packageFocus)"
                    :target-sequence="traceTargetSequence(packageFocus)"
                    height="100%"
                  />
                  <FilePreviewer
                    v-else
                    :key="`package-${packageFocus.file_id}`"
                    class="package-preview-body"
                    :source-url="storedFilePreviewUrl(packageFocus.file_id)"
                    :file-name="packageFocus.original_name"
                    :mime-type="packageFocus.mime_type"
                    height="100%"
                  />
                </template>
              </aside>
            </div>
          </div>
          <div v-else-if="!currentFile" class="stage-empty">
            <el-icon><Picture /></el-icon>
            <strong>还没有结果文件</strong>
            <p>从左侧上传胶图或质检文件。</p>
          </div>
          <div v-else-if="isImage(currentFile)" v-loading="imagePreviewLoading" class="stage-empty">
            <el-icon><Picture /></el-icon>
            <strong>{{ imagePreviewError || '正在读取图片' }}</strong>
            <el-button v-if="imagePreviewError" plain size="small" @click="loadPreview(currentFile)">
              重试
            </el-button>
          </div>
          <AbiTracePreview
            v-else-if="isTrace(currentFile)"
            :key="`link-${currentFile.id}`"
            class="stage-document-preview"
            :source-url="linkedFilePreviewUrl(currentFile.id)"
            :direction="traceDirection(currentFile)"
            :primer-label="primerLabel(currentFile)"
            :target-sequence="traceTargetSequence(currentFile)"
            height="100%"
          />
          <SeqReadPreview
            v-else-if="isSequence(currentFile)"
            :key="`link-seq-${currentFile.id}`"
            class="stage-document-preview"
            :source-url="linkedFilePreviewUrl(currentFile.id)"
            :direction="traceDirection(currentFile)"
            :primer-label="primerLabel(currentFile)"
            :target-sequence="traceTargetSequence(currentFile)"
            height="100%"
          />
          <FilePreviewer
            v-else
            :key="`link-${currentFile.id}`"
            class="stage-document-preview"
            :source-url="linkedFilePreviewUrl(currentFile.id)"
            :file-name="currentFile.original_name"
            :mime-type="currentFile.mime_type"
            height="100%"
          />
          <div
            v-for="(entry, index) in regionEntries"
            :key="entry.key"
            class="qc-region-overlay"
            :class="{ 'is-drawing': entry.draft, 'is-label-below': regionLabelBelow(entry.region) }"
            :style="regionOverlayStyle(entry.region)"
          >
            <span class="qc-region-label">
              <el-popover
                v-if="!entry.draft"
                :visible="regionRenameIndex === index"
                :placement="regionLabelBelow(entry.region) ? 'bottom-start' : 'top-start'"
                trigger="click"
                :width="230"
                @update:visible="setRegionRenameVisible(index, $event)"
                @after-enter="focusRegionRenameInput(index)"
              >
                <div class="rename-popover-content">
                  <strong>标记命名</strong>
                  <el-input
                    :ref="`regionRenameInput-${index}`"
                    v-model="regionRenameDraft"
                    maxlength="24"
                    placeholder="例如 H链、目标条带"
                    @keydown.enter.prevent="saveRegionRename"
                  />
                  <div class="rename-popover-actions">
                    <el-button size="small" @click="closeRegionRename">取消</el-button>
                    <el-button size="small" type="primary" @click="saveRegionRename">保存</el-button>
                  </div>
                </div>
                <template #reference>
                  <button
                    type="button"
                    title="点击修改标记名称"
                    @mousedown.stop
                    @click.stop
                  >
                    {{ regionDisplayName(entry.region, index) }}
                  </button>
                </template>
              </el-popover>
              <button
                v-else
                type="button"
                title="正在框选"
                @mousedown.stop
                @click.stop
              >
                新选区
              </button>
              <button
                v-if="!entry.draft"
                class="qc-region-remove"
                type="button"
                title="删除这个标记"
                aria-label="删除这个标记"
                @mousedown.stop
                @click.stop="removeRegion(index)"
              >
                ×
              </button>
            </span>
          </div>
        </div>

        <footer v-if="showGelStage" class="viewer-footer">
          <span class="viewer-gesture-hint">左键拖动 · 滚轮缩放 · Shift + 左键框选</span>
          <div class="viewport-tools">
            <button type="button" aria-label="向左旋转" title="向左旋转 90°" @click="rotateBy(-90)">
              <el-icon><RefreshLeft /></el-icon>
            </button>
            <button type="button" aria-label="向右旋转" title="向右旋转 90°" @click="rotateBy(90)">
              <el-icon><RefreshRight /></el-icon>
            </button>
            <span class="tool-separator" />
            <button
              class="fill-button"
              type="button"
              :title="viewMode === 'fit' ? '铺满预览窗口，图片边缘可能被裁切' : '恢复图片完整显示'"
              @click="toggleFillView"
            >
              {{ viewMode === 'fit' ? '填充窗口' : '适应窗口' }}
            </button>
            <span class="tool-separator" />
            <button type="button" aria-label="缩小" title="缩小" @click="zoomBy(1 / 1.25)">
              <el-icon><ZoomOut /></el-icon>
            </button>
            <b>{{ Math.round(view.zoom * 100) }}%</b>
            <button type="button" aria-label="放大" title="放大" @click="zoomBy(1.25)">
              <el-icon><ZoomIn /></el-icon>
            </button>
            <span class="tool-separator" />
            <button
              type="button"
              :aria-label="isFullscreen ? '退出全屏' : '全屏预览'"
              :title="isFullscreen ? '退出全屏（Esc）' : '全屏预览'"
              @click="toggleFullscreen"
            >
              <el-icon><FullScreen /></el-icon>
            </button>
          </div>
        </footer>
      </section>

      <aside class="record-inspector">
        <header class="inspector-heading">
          <strong>工单信息</strong>
        </header>
        <nav class="inspector-tabs" aria-label="工单信息分组">
          <button
            type="button"
            :class="{ 'is-active': activeInspector === 'summary' }"
            @click="activeInspector = 'summary'"
          >
            质检判读
          </button>
          <button
            type="button"
            :class="{ 'is-active': activeInspector === 'sample' }"
            @click="activeInspector = 'sample'"
          >
            样品信息
          </button>
          <button
            type="button"
            :class="{ 'is-active': activeInspector === 'record' }"
            @click="activeInspector = 'record'"
          >
            建库记录
          </button>
        </nav>

        <div class="inspector-scroll">
          <section v-show="activeInspector === 'summary'" class="inspector-section">
            <dl class="metric-list">
              <div v-for="item in keyMetrics" :key="item.label">
                <dt>{{ item.label }}</dt>
                <dd :title="item.value">{{ item.value }}</dd>
              </div>
            </dl>
            <el-form size="small" class="inspector-form" @submit.prevent>
              <div class="field-grid">
                <el-form-item label="质检结论">
                  <el-select
                    v-model="order.qc_result"
                    clearable
                    :disabled="!canEditQc"
                    @change="persist('qc_result')"
                  >
                    <el-option v-for="item in qcResultOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
                <el-form-item label="质检人">
                  <SerumUserSelect
                    v-model="order.qc_owner"
                    :options="selectedUserOptions(order.qc_owner)"
                    placeholder="选择质检人"
                    :disabled="!canEditQc"
                    clearable
                    @change="persist('qc_owner')"
                  />
                </el-form-item>
                <el-form-item label="质检日期">
                  <el-date-picker
                    v-model="order.qc_on"
                    type="date"
                    value-format="YYYY-MM-DD"
                    format="YYYY-MM-DD"
                    placeholder="选择日期"
                    :disabled="!canEditQc"
                    @change="persist('qc_on')"
                  />
                </el-form-item>
                <el-form-item label="质检说明" class="is-wide">
                  <el-input
                    v-model="order.qc_note"
                    type="textarea"
                    :autosize="{ minRows: 4, maxRows: 8 }"
                    :disabled="!canEditQc"
                    placeholder="记录条带判读、引物核对或重做建议"
                    @blur="persist('qc_note')"
                  />
                </el-form-item>
              </div>
            </el-form>
          </section>

          <el-form
            v-show="activeInspector === 'sample' || activeInspector === 'record'"
            size="small"
            class="inspector-form"
            @submit.prevent
          >
            <section
              v-for="section in activeFieldSections"
              :key="section.title"
              class="inspector-section"
            >
              <div class="section-heading">
                <strong>{{ section.title }}</strong>
              </div>
              <div class="field-grid">
                <template v-for="field in section.fields" :key="field.key">
                <el-form-item
                  :label="field.label"
                  :label-width="field.type === 'primer-matrix' ? '0' : undefined"
                  :class="{ 'is-wide': field.wide }"
                >
                  <el-date-picker
                    v-if="field.type === 'date'"
                    v-model="order[field.key]"
                    type="date"
                    value-format="YYYY-MM-DD"
                    format="YYYY-MM-DD"
                    placeholder="选择日期"
                    :disabled="!canEdit"
                    @change="persist(field.key)"
                  />
                  <WorkbenchTargetSelect
                    v-else-if="field.type === 'target'"
                    v-model="order.target_codes"
                    :display-name="order.target_name"
                    :placeholder="order.target_name ? '' : '搜索靶点'"
                    :disabled="!canEdit"
                    @change="onTargetChange"
                  />
                  <SerumUserSelect
                    v-else-if="field.type === 'user'"
                    v-model="order[field.key]"
                    :options="selectedUserOptions(order[field.key])"
                    :placeholder="`选择${field.label}`"
                    :disabled="!canEdit"
                    clearable
                    @change="persist(field.key)"
                  />
                  <div
                    v-else-if="field.type === 'source-link'"
                    class="source-link"
                    :class="{ 'is-link': Boolean(order[field.key]) }"
                    @click="openSourceDiscovery(order[field.key])"
                  >
                    <el-input :model-value="order[field.key] || '手工创建'" readonly>
                      <template v-if="order[field.key]" #suffix>
                        <span class="source-link-action">查看</span>
                      </template>
                    </el-input>
                  </div>
                  <div v-else-if="field.type === 'primer-matrix'" class="primer-matrix">
                    <span />
                    <span class="primer-matrix-heading">正向引物</span>
                    <span class="primer-matrix-heading">反向引物</span>
                    <span class="primer-matrix-heading">浓度</span>
                    <template v-for="primer in field.rows" :key="primer.chain">
                      <strong class="primer-chain">{{ primer.chain }}</strong>
                      <el-select
                        v-model="order[primer.forward.key]"
                        allow-create
                        clearable
                        filterable
                        remote
                        reserve-keyword
                        :loading="catalogLoading"
                        :remote-method="searchCatalog"
                        :disabled="!canEdit"
                        @change="(value) => onCatalogChange(primer.forward, value)"
                        @visible-change="(visible) => visible && searchCatalog('')"
                      >
                        <el-option v-for="item in catalogOptions" :key="item.id" :label="item.name" :value="item.name" />
                      </el-select>
                      <el-select
                        v-model="order[primer.reverse.key]"
                        allow-create
                        clearable
                        filterable
                        remote
                        reserve-keyword
                        :loading="catalogLoading"
                        :remote-method="searchCatalog"
                        :disabled="!canEdit"
                        @change="(value) => onCatalogChange(primer.reverse, value)"
                        @visible-change="(visible) => visible && searchCatalog('')"
                      >
                        <el-option v-for="item in catalogOptions" :key="item.id" :label="item.name" :value="item.name" />
                      </el-select>
                      <el-input
                        v-model="order[primer.concentrationKey]"
                        :disabled="!canEdit"
                        @blur="persist(primer.concentrationKey)"
                      />
                    </template>
                  </div>
                  <el-select
                    v-else-if="field.type === 'catalog-select'"
                    v-model="order[field.key]"
                    allow-create
                    clearable
                    filterable
                    remote
                    reserve-keyword
                    :loading="catalogLoading"
                    :remote-method="searchCatalog"
                    :disabled="!canEdit"
                    @change="(value) => onCatalogChange(field, value)"
                    @visible-change="(visible) => visible && searchCatalog('')"
                  >
                    <el-option
                      v-for="item in catalogOptions"
                      :key="item.id"
                      :label="item.name"
                      :value="item.name"
                    >
                      <span>{{ item.name }}</span>
                      <span v-if="item.short_sequence" class="catalog-sequence">{{ item.short_sequence }}</span>
                    </el-option>
                  </el-select>
                  <el-select
                    v-else-if="['select', 'source-select'].includes(field.type)"
                    v-model="order[field.key]"
                    :clearable="!isRequiredChoice(field.key)"
                    :disabled="!canEditField(field.key)"
                    @change="persist(field.key)"
                  >
                    <el-option
                      v-for="item in fieldOptions(field)"
                      :key="item.value || item"
                      :label="item.label || item"
                      :value="item.value || item"
                    />
                  </el-select>
                  <el-input
                    v-else-if="field.type === 'plate-list'"
                    :model-value="plateDraft"
                    type="textarea"
                    :autosize="{ minRows: 1, maxRows: 6 }"
                    resize="none"
                    placeholder="输入板号；回车、逗号或制表符均可分隔"
                    :disabled="!canEdit"
                    @update:model-value="onPlateDraftInput"
                    @blur="persist('plate_nos')"
                  />
                  <el-input
                    v-else
                    v-model="order[field.key]"
                    :disabled="!canEdit"
                    :type="field.type === 'textarea' ? 'textarea' : 'text'"
                    :autosize="field.type === 'textarea' ? { minRows: 2, maxRows: 5 } : undefined"
                    :placeholder="field.placeholder || ''"
                    @blur="persist(field.key)"
                  />
                </el-form-item>
                <div v-if="field.rowBreak" class="field-row-break" aria-hidden="true" />
                </template>
              </div>
            </section>

          </el-form>
        </div>
      </aside>
    </main>
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import {
  ArrowLeft,
  Collection,
  Delete,
  Document,
  DocumentCopy,
  Download,
  FolderOpened,
  FullScreen,
  Grid,
  Monitor,
  VideoPlay,
  Picture,
  RefreshLeft,
  RefreshRight,
  UploadFilled,
  ZoomIn,
  ZoomOut,
} from '@element-plus/icons-vue'
import {
  ElButton,
  ElDatePicker,
  ElForm,
  ElFormItem,
  ElIcon,
  ElImage,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPopover,
  ElSelect,
  ElSlider,
} from 'element-plus'
import { useUserStore } from '@vben/stores'

import {
  deleteLibraryResult,
  fetchLibraryFiles,
  libraryStoredFileDownloadUrl,
  fetchPrimerIndexOptions,
  libraryFileDownloadUrl,
  saveLibraryOrder,
  updateLibraryFile,
  uploadLibraryFileBatch,
} from '#/api/molecularLibrary'
import { expandResultArchives, readDroppedFiles, resultUploadLimitError } from './readDroppedFiles'
import { extractApiError, notifyApiError } from '#/api/errors'
import { FilePreviewer } from '#/components/file-preview'
import { WorkbenchStatusEditor, WorkbenchTargetSelect } from '#/components/workbench'
import { downloadFile, fetchFileBlob } from '#/utils/file-resource'
import { canEditLibrary, canManageLibraryFiles } from '#/utils/molecularPermission'
import { rememberDiscoveryFocus } from '#/views/Discovery/workbench/DiscoveryWorkbench.vue'
import { getSerumUserName } from '#/utils/serumPermission'
import { getTiterPriorityTone, WORKBENCH_PRIORITY_DEFAULT } from '#/utils/serumProjectStatus'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'
import SerumUserSelect from '../../Serum/shared/SerumUserSelect.vue'
import {
  BUILD_PERIPHERAL_BLOOD,
  BUILD_PHAGE_DISPLAY,
  BUILD_PHAGE_NGS,
  BUILD_PLATE,
  BUILD_POOLED_BARCODE,
  BUILD_POOLED_BCR,
  buildTypeLabel,
  mouseCategoryLabel,
  normalizePlateInputText,
  optionsForBuild,
  orderEditorSections,
  plateNumbersFromText,
  persistValue,
  plateNumbersText,
  PRIORITY_OPTIONS,
  QC_RESULT_OPTIONS,
  REQUIRED_CHOICE_KEYS,
  SAMPLE_SOURCE_OPTIONS,
  sampleSourceLabel,
  sampleTypeLabel,
  stampQcFields,
  STATUS_OPTIONS,
  statusTone,
  typeGroup,
} from './libraryColumns'

const IMAGE_EXT = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
const VIDEO_EXT = ['mp4', 'webm', 'ogg', 'ogv', 'mov']
const BARCODE_BUILDS = new Set([BUILD_POOLED_BARCODE, BUILD_PHAGE_NGS, BUILD_PERIPHERAL_BLOOD])
const FORWARD_ARM_1 = 'ACCGAGATCTACAC'
const FORWARD_ARM_2 = 'ACACTCTTTCC'
const REVERSE_ARM_1 = 'AACTCCAGTCAC'
const REVERSE_ARM_2 = 'ATCTCGTATGCC'
const PRIMER_TARGET_LABELS = {
  i5: 'i5',
  i7: 'i7',
  hF: 'H正向',
  hR: 'H反向',
  kF: 'K正向',
  kR: 'K反向',
  lF: 'L正向',
  lR: 'L反向',
}
const AbiTracePreview = defineAsyncComponent(() => import('./AbiTracePreview.vue'))
const SeqReadPreview = defineAsyncComponent(() => import('./SeqReadPreview.vue'))
const ZOOM_MIN = 0.2
const ZOOM_MAX = 8
const MAX_QC_REGIONS = 20

function reverseComplement(value) {
  const complement = { A: 'T', C: 'G', G: 'C', T: 'A', N: 'N' }
  return String(value || '')
    .toUpperCase()
    .replace(/[^ACGTN]/g, '')
    .split('')
    .reverse()
    .map((base) => complement[base] || base)
    .join('')
}

function assembledCheck(primer, direction) {
  const body = reverseComplement(primer)
  if (!body) return ''
  return direction === 'F'
    ? `${FORWARD_ARM_1}${body}${FORWARD_ARM_2}`
    : `${REVERSE_ARM_1}${body}${REVERSE_ARM_2}`
}

const PRIMER_RESULT_FIELDS = ['index_mode', 'i5_sequence', 'i7_sequence']

function qcUploadNotice(summary) {
  const outcomes = summary.map((item) => item.outcome)
  const linked = summary.reduce((total, item) => total + Number(item.newly_linked || 0), 0)
  const orders = summary.flatMap((item) => item.orders || [])
  const details = [...new Set(orders.map((item) => String(item.detail || '').trim()).filter(Boolean))]
  const detail = details.join('；')
  const held = orders.some((item) => item.status === '质检待确认' || item.status === '质检不通过')
  const passed = orders.length > 0 && orders.every((item) => item.status === '质检通过' || item.status === '已完成')
  const saved = outcomes.some((outcome) => outcome && outcome !== 'skipped')
  if (!saved) return { type: 'warning', text: '没有文件被保存，请查看未保存原因' }
  if (!linked && outcomes.every((outcome) => outcome === 'already' || outcome === 'skipped')) {
    return { type: 'info', text: detail ? `这些文件已经上传过，${detail}` : '这些文件已经上传过' }
  }
  const lead = '已上传并关联当前工单'
  if (held) return { type: 'warning', text: detail ? `${lead}，${detail}` : `${lead}，引物未对上` }
  if (passed) return { type: 'success', text: detail ? `${lead}，${detail}，质检通过` : `${lead}，质检通过` }
  return { type: 'success', text: detail ? `${lead}，${detail}` : lead }
}

export default {
  name: 'LibraryConstructionResult',
  components: {
    AbiTracePreview,
    SeqReadPreview,
    ArrowLeft,
    Delete,
    Document,
    Download,
    FullScreen,
    ElButton,
    ElDatePicker,
    ElForm,
    ElFormItem,
    ElIcon,
    ElImage,
    ElInput,
    ElOption,
    ElPopover,
    ElSelect,
    ElSlider,
    FilePreviewer,
    FolderOpened,
    Picture,
    RefreshLeft,
    RefreshRight,
    SerumUserSelect,
    UploadFilled,
    WorkbenchStatusEditor,
    WorkbenchTargetSelect,
    ZoomIn,
    ZoomOut,
  },
  data() {
    return {
      loading: false,
      loadRequest: 0,
      activeInspector: 'summary',
      order: {},
      plateDraft: '',
      files: [],
      resultUploading: false,
      packages: [],
      selectedPackage: null,
      packageFocus: null,
      packagePath: '',
      packageSelectedKey: '',
      currentFileId: null,
      catalogOptions: [],
      catalogLoading: false,
      fileObjectUrls: {},
      fileSaveVersions: {},
      imagePreviewLoading: false,
      imagePreviewError: '',
      fileRenameOpen: false,
      fileRenameDraft: '',
      baseline: {},
      tabDataFetchedAt: 0,
      isFullscreen: false,
      panning: false,
      panOrigin: null,
      regionDrawing: false,
      regionStart: null,
      regionDraft: null,
      regionRenameIndex: null,
      regionRenameDraft: '',
      pendingRegionRenameIndex: null,
      imageRect: null,
      viewMode: 'fit',
      view: { zoom: 1, x: 0, y: 0, rotation: 0, brightness: 100, contrast: 100, invert: false },
    }
  },
  computed: {
    orderId() {
      if (this.$route.name !== 'LibraryConstructionResult') return 0
      return Number(this.$route.query.id)
    },
    canEdit() {
      return canEditLibrary(useUserStore().userInfo)
    },
    canManageFiles() {
      return canManageLibraryFiles(useUserStore().userInfo)
    },
    canEditQc() {
      return this.canEdit || this.canManageFiles
    },
    pageTitle() {
      return this.order.library_order_id || this.order.library_code || '文库质控'
    },
    detailSubtitle() {
      const targetCodes = Array.isArray(this.order.target_codes)
        ? this.order.target_codes.filter(Boolean).join('、')
        : String(this.order.target_codes || '').trim()
      const target = [this.order.target_name, targetCodes].filter(Boolean).join(' · ')
      return [buildTypeLabel(this.order.build_type), target].filter(Boolean).join(' ｜ ') || '文库构建工单'
    },
    currentStatus() {
      return this.order.status || '待处理'
    },
    currentPriority() {
      return this.order.priority || WORKBENCH_PRIORITY_DEFAULT
    },
    statusOptions() {
      return STATUS_OPTIONS
    },
    priorityOptions() {
      return PRIORITY_OPTIONS
    },
    qcResultOptions() {
      return QC_RESULT_OPTIONS
    },
    statusTagType() {
      return statusTone(this.currentStatus)
    },
    priorityTone() {
      return getTiterPriorityTone(this.currentPriority)
    },
    priorityTagType() {
      const tone = this.priorityTone
      return tone === 'king' ? 'info' : tone
    },
    group() {
      return typeGroup(this.order.build_type)
    },
    headerMeta() {
      return [
        { label: '建库编号', value: this.order.library_code || '—' },
        { label: '负责人', value: this.order.owner || '待分配' },
        { label: '开始 / 完成', value: `${this.order.started_at || '—'} → ${this.order.finished_at || '—'}` },
      ]
    },
    sampleFacts() {
      return [
        { label: '项目', value: this.order.source_project_code || '—' },
        { label: '靶点', value: this.order.target_name || '—' },
        { label: '归类鼠型', value: mouseCategoryLabel(this.order.mouse_model) || '—' },
        { label: '样品类型', value: sampleTypeLabel(this.order.sample_type) || '—' },
        { label: '样品来源', value: sampleSourceLabel(this.order.sample_source) || '—' },
        { label: '交接日期', value: this.order.received_on || '—' },
      ]
    },
    sampleSections() {
      const sections = orderEditorSections(this.group, this.order)
      return [{
        title: '样品与来源',
        fields: [
          ...(sections.find((item) => item.title === '基本信息')?.fields || []),
          ...(sections.find((item) => item.title === '样品交接')?.fields || []),
        ],
      }]
    },
    recordSections() {
      return orderEditorSections(this.group, this.order)
        .filter((item) => !['基本信息', '样品交接', '质控结果'].includes(item.title))
        .map((item) => item.title === '工单安排'
          ? { ...item, fields: item.fields.filter((field) => !['status', 'priority'].includes(field.key)) }
          : item)
    },
    activeFieldSections() {
      return this.activeInspector === 'sample' ? this.sampleSections : this.recordSections
    },
    keyMetrics() {
      const metrics = [
        { label: '建库类型', value: buildTypeLabel(this.order.build_type) || '—' },
        { label: '负责人', value: this.order.owner || '待分配' },
      ]
      if (this.group === BUILD_PLATE) {
        const plates = (this.order.plate_nos || []).join('、')
        metrics.push({ label: '板号', value: plates || '—' })
        metrics.push({ label: '阳性细胞数', value: this.order.positive_cell_count ?? '—' })
      }
      if (this.group === BUILD_POOLED_BCR) {
        metrics.push({ label: '阳性细胞数', value: this.order.positive_cell_count ?? '—' })
        metrics.push({ label: 'cDNA 浓度', value: this.order.cdna_concentration || '—' })
        metrics.push({ label: '文库浓度', value: this.order.library_concentration || '—' })
      }
      if (this.group === BUILD_PHAGE_DISPLAY) {
        metrics.push({ label: '样品来源', value: sampleSourceLabel(this.order.sample_source) || '—' })
        metrics.push({ label: '初始库容', value: this.order.initial_library_size || '—' })
        metrics.push({ label: '有效库容', value: this.order.effective_library_size || '—' })
      }
      if (this.group === BUILD_PHAGE_NGS) {
        metrics.push({ label: '建库批号', value: this.order.library_batch_no || '—' })
        metrics.push({ label: '片段大小', value: this.order.fragment_size_bp ? `${this.order.fragment_size_bp} bp` : '—' })
      }
      metrics.push({ label: '完成时间', value: this.order.finished_at || '—' })
      return metrics
    },
    gelFiles() {
      return this.files.filter((file) => this.isImage(file))
    },
    qcGaps() {
      const status = this.currentStatus
      if (!this.order?.id || ['已取消', '已完成', '质检不通过'].includes(status)) return []
      const working = ['建库中', '待质检', '质检待确认', '质检通过'].includes(status) || this.files.length
      if (!working) return []
      const gaps = []
      const reads = this.files.filter((file) => (
        !file.replaced && ['SEQ', 'AB1', 'ABI'].includes(this.fileExt(file.original_name))
      ))
      const unmatched = reads.filter((file) => file.sequence_status === 'not_found')
      const armOnly = reads.filter((file) => file.sequence_status === 'arm_only')
      if (unmatched.length) {
        gaps.push({ text: '引物未对上', title: `${unmatched.length} 个测序文件没对上引物`, tone: 'is-fail' })
      }
      if (armOnly.length) {
        gaps.push({ text: '引物不对', title: '同源臂对上，中间的引物不对', tone: 'is-fail' })
      }
      const required = []
      if (this.order.build_type === 'pooled_bcr') {
        ;[
          ['h_forward_primer_id', 'hF'],
          ['h_reverse_primer_id', 'hR'],
          ['k_forward_primer_id', 'kF'],
          ['k_reverse_primer_id', 'kR'],
          ['l_forward_primer_id', 'lF'],
          ['l_reverse_primer_id', 'lR'],
        ].forEach(([key, target]) => {
          if (this.order[key]) required.push(target)
        })
      } else if (BARCODE_BUILDS.has(this.order.build_type)) {
        const mode = this.order.index_mode
        if (['single_i5', 'dual'].includes(mode) && String(this.order.i5_sequence || '').trim()) required.push('i5')
        if (['single_i7', 'dual'].includes(mode) && String(this.order.i7_sequence || '').trim()) required.push('i7')
      }
      const matchedTargets = new Set(
        reads.filter((file) => file.sequence_status === 'matched').map((file) => file.sequence_target),
      )
      const failedTargets = new Set([...unmatched, ...armOnly].map((file) => file.sequence_target))
      if (reads.length && required.some((target) => !matchedTargets.has(target) && !failedTargets.has(target))) {
        gaps.push({ text: '引物未齐', title: '需要的引物还没对全', tone: 'is-warn' })
      }
      if (!reads.length && (this.gelFiles.length || ['待质检', '质检待确认'].includes(status))) {
        gaps.push({ text: '缺测序', title: '还没有测序结果', tone: 'is-warn' })
      }
      if (reads.length && !this.gelFiles.length) gaps.push({ text: '缺胶图', title: '还没有胶图', tone: 'is-warn' })
      const fieldKeys = new Set(
        orderEditorSections(this.order.build_type, this.order)
          .flatMap((section) => section.fields || [])
          .map((field) => field.key),
      )
      if (fieldKeys.has('rna_location') && !String(this.order.rna_location || '').trim()) {
        gaps.push({ text: '缺 RNA', title: 'RNA 位置没填', tone: 'is-warn' })
      }
      if (fieldKeys.has('cdna_location') && !String(this.order.cdna_location || '').trim()) {
        gaps.push({ text: '缺 cDNA', title: 'cDNA 位置没填', tone: 'is-warn' })
      }
      return gaps
    },
    currentFile() {
      return this.files.find((file) => file.id === this.currentFileId) || null
    },
    packageBreadcrumbs() {
      const parts = this.packagePath.split('/').filter(Boolean)
      return parts.map((name, index) => ({
        name,
        path: parts.slice(0, index + 1).join('/'),
      }))
    },
    packageBrowserEntries() {
      const prefix = this.packagePath ? `${this.packagePath}/` : ''
      const folders = new Map()
      const files = []
      const packageFiles = this.selectedPackage?.files || []
      packageFiles.forEach((file) => {
        const relative = String(file.relative_path || file.original_name || '').replaceAll('\\', '/')
        if (!relative.startsWith(prefix)) return
        const rest = relative.slice(prefix.length).split('/').filter(Boolean)
        if (!rest.length) return
        if (rest.length > 1) {
          const name = rest[0]
          const path = `${prefix}${name}`.replace(/\/$/, '')
          const entry = folders.get(name) || {
            key: `folder:${path}`,
            type: 'folder',
            name,
            path,
            count: 0,
          }
          entry.count += 1
          folders.set(name, entry)
          return
        }
        files.push({
          key: `file:${file.file_id}`,
          type: 'file',
          name: file.original_name || rest[0],
          file,
        })
      })
      const byName = (left, right) => left.name.localeCompare(right.name, 'zh-CN', { numeric: true })
      return [...folders.values()].sort(byName).concat(files.sort(byName))
    },
    fileRenameSuffix() {
      const currentName = this.currentFile?.original_name || ''
      const suffixIndex = currentName.lastIndexOf('.')
      return suffixIndex > 0 ? currentName.slice(suffixIndex) : ''
    },
    showGelStage() {
      const file = this.currentFile
      if (!file || !this.isImage(file) || this.imagePreviewError) return false
      if (file.preview_object_url) return true
      return Boolean(this.imagePreviewLoading && file.thumb_object_url)
    },
    gelSource() {
      return this.currentFile?.preview_object_url || this.currentFile?.thumb_object_url || ''
    },
    stageStyle() {
      const { zoom, x, y, rotation, brightness, contrast, invert } = this.view
      const filters = [`brightness(${brightness / 100})`, `contrast(${contrast / 100})`]
      if (invert) filters.push('invert(1)')
      return {
        transform: `translate3d(${x}px, ${y}px, 0) scale(${zoom}) rotate(${rotation || 0}deg)`,
        filter: filters.join(' '),
      }
    },
    isEnhanced() {
      return this.view.brightness === 190 && this.view.contrast === 150
    },
    currentRegions() {
      return Array.isArray(this.currentFile?.qc_regions) ? this.currentFile.qc_regions : []
    },
    regionEntries() {
      if (!this.showGelStage || !this.imageRect) return []
      const entries = this.currentRegions.map((region, index) => ({
        key: `stored-${index}`,
        region,
        draft: false,
      }))
      if (this.regionDraft) {
        entries.push({ key: 'draft', region: this.regionDraft, draft: true })
      }
      return entries
    },
    sourceOptions() {
      return optionsForBuild(SAMPLE_SOURCE_OPTIONS, this.order.build_type)
    },
  },
  created() {
    this.load()
  },
  mounted() {
    this.bindViewerListeners()
  },
  activated() {
    this.bindViewerListeners()
    if (shouldRefreshTabData(this.tabDataFetchedAt)) this.load()
  },
  deactivated() {
    this.unbindViewerListeners()
    this.endPan()
    this.endRegionDrawing()
  },
  beforeUnmount() {
    this.loadRequest += 1
    this.endPan()
    this.endRegionDrawing()
    this.unbindViewerListeners()
    this.revokeObjectUrls()
  },
  watch: {
    '$route.query.id'() {
      if (this.$route.name !== 'LibraryConstructionResult') return
      this.currentFileId = null
      this.load()
    },
  },
  methods: {
    packageEntryIcon(entry) {
      return entry?.type === 'folder' ? FolderOpened : this.fileIcon(entry?.name)
    },
    packageEntryClass(entry) {
      return entry?.type === 'folder' ? 'is-folder' : this.fileIconClass(entry?.name)
    },
    storedFilePreviewUrl(fileId) {
      return libraryStoredFileDownloadUrl(fileId, '&preview=true')
    },
    linkedFilePreviewUrl(linkId) {
      return libraryFileDownloadUrl(linkId, '&preview=true')
    },
    fieldOptions(field) {
      if (field.type === 'source-select') return this.sourceOptions
      return field.options || []
    },
    async searchCatalog(query = '') {
      this.catalogLoading = true
      try {
        const data = await fetchPrimerIndexOptions({ query, limit: 100 })
        this.catalogOptions = data?.items || []
      } catch {
        this.catalogOptions = []
      } finally {
        this.catalogLoading = false
      }
    },
    async onCatalogChange(field, value) {
      const selected = this.catalogOptions.find((item) => item.name === value)
      this.order[field.catalogIdKey] = selected?.id || null
      if (field.sequenceKey) this.order[field.sequenceKey] = selected?.short_sequence || ''
      const payload = {
        id: this.order.id,
        [field.key]: value || null,
        [field.catalogIdKey]: this.order[field.catalogIdKey],
      }
      if (field.sequenceKey) payload[field.sequenceKey] = this.order[field.sequenceKey] || null
      try {
        await saveLibraryOrder(payload)
        await this.load()
      } catch (error) {
        this.order = JSON.parse(JSON.stringify(this.baseline))
        notifyApiError(error, { messages: { default: '保存引物或Index失败' } })
      }
    },
    goBack() {
      this.$router.push('/molecular-cell/library-construction')
    },
    selectedUserOptions(value) {
      const text = String(value || '').trim()
      return text ? [text] : []
    },
    canEditField(key) {
      if (!this.canEdit) return false
      if (key === 'build_type') return this.currentStatus === '待处理'
      return true
    },
    isRequiredChoice(key) {
      return REQUIRED_CHOICE_KEYS.includes(key)
    },
    sameValue(left, right) {
      return JSON.stringify(left ?? null) === JSON.stringify(right ?? null)
    },
    async load(preferId) {
      const orderId = this.orderId
      if (!orderId) return
      const request = ++this.loadRequest
      this.endRegionDrawing()
      this.imageRect = null
      this.loading = true
      const startedFileId = this.currentFileId
      const startedPackageId = this.selectedPackage?.id
      const startedPackageFileId = this.packageFocus?.file_id
      const startedPackagePath = this.packagePath
      try {
        const data = await fetchLibraryFiles(orderId)
        if (request !== this.loadRequest || orderId !== this.orderId) return
        const userMoved = this.currentFileId !== startedFileId
          || this.selectedPackage?.id !== startedPackageId
          || this.packageFocus?.file_id !== startedPackageFileId
          || this.packagePath !== startedPackagePath
        const keepId = userMoved ? this.currentFileId : (preferId || startedFileId)
        const keepPackageId = userMoved ? this.selectedPackage?.id : startedPackageId
        const keepPackageFileId = userMoved ? this.packageFocus?.file_id : startedPackageFileId
        const keepPackagePath = userMoved ? this.packagePath : startedPackagePath
        this.revokeObjectUrls()
        this.order = data?.order || {}
        this.order.primer_sequences = data?.primer_sequences || {}
        if (!Array.isArray(this.order.target_codes)) this.order.target_codes = []
        if (!Array.isArray(this.order.plate_nos)) this.order.plate_nos = []
        this.plateDraft = plateNumbersText(this.order.plate_nos)
        this.baseline = JSON.parse(JSON.stringify(this.order))
        this.files = data?.items || []
        this.sortFiles()
        this.packages = data?.packages || []
        this.tabDataFetchedAt = Date.now()
        this.selectedPackage = this.packages.find((item) => item.id === keepPackageId) || null
        this.packageFocus = this.selectedPackage?.files?.find(
          (item) => item.file_id === keepPackageFileId,
        ) || null
        this.packagePath = this.selectedPackage ? keepPackagePath : ''
        this.packageSelectedKey = this.packageFocus
          ? `file:${this.packageFocus.file_id}`
          : ''
        const next = this.selectedPackage
          ? null
          : this.files.find((file) => file.id === keepId)
            || this.gelFiles[0]
            || this.files[0]
            || null
        this.currentFileId = next?.id || null
        this.resetView()
        this.loadImageThumbs()
        if (next) this.loadPreview(next)
      } catch (error) {
        if (request !== this.loadRequest || orderId !== this.orderId) return
        const failure = extractApiError(error)
        const missing = failure.httpStatus === 404
          || failure.backendMessage === '文库构建工单不存在'
        notifyApiError(error, {
          messages: {
            notFound: '文库工单不存在或已删除',
            default: '加载详情失败',
          },
        })
        if (missing) {
          this.loading = false
          await this.$router.replace('/molecular-cell/library-construction')
        }
      } finally {
        if (request === this.loadRequest && orderId === this.orderId) this.loading = false
      }
    },
    bindViewerListeners() {
      window.addEventListener('keydown', this.onViewerKeydown)
      window.addEventListener('resize', this.syncRegionOverlay)
    },
    unbindViewerListeners() {
      window.removeEventListener('keydown', this.onViewerKeydown)
      window.removeEventListener('resize', this.syncRegionOverlay)
    },
    fileExt(name) {
      const text = String(name || '')
      const ext = text.includes('.') ? text.split('.').pop() : ''
      return (ext || 'FILE').toUpperCase()
    },
    fileIcon(name) {
      const ext = this.fileExt(name).toLowerCase()
      if (['xls', 'xlsx', 'csv'].includes(ext)) return Grid
      if (['doc', 'docx'].includes(ext)) return DocumentCopy
      if (['ppt', 'pptx'].includes(ext)) return Monitor
      if (ext === 'pdf') return Collection
      if (['zip', 'rar', '7z'].includes(ext)) return FolderOpened
      if (['mp4', 'webm', 'ogg', 'ogv', 'mov'].includes(ext)) return VideoPlay
      return Document
    },
    fileIconClass(name) {
      const ext = this.fileExt(name).toLowerCase()
      if (['xls', 'xlsx', 'csv'].includes(ext)) return 'is-excel'
      if (['doc', 'docx'].includes(ext)) return 'is-word'
      if (['ppt', 'pptx'].includes(ext)) return 'is-ppt'
      if (ext === 'pdf') return 'is-pdf'
      if (['zip', 'rar', '7z'].includes(ext)) return 'is-zip'
      if (['ab1', 'abi'].includes(ext)) return 'is-trace'
      if (['seq', 'clc', 'fasta', 'fa'].includes(ext)) return 'is-sequence'
      if (ext === 'txt') return 'is-text'
      if (['mp4', 'webm', 'ogg', 'ogv', 'mov'].includes(ext)) return 'is-video'
      return ''
    },
    isImage(file) {
      const name = String(file?.original_name || '').toLowerCase()
      const ext = name.includes('.') ? name.split('.').pop() : ''
      if (IMAGE_EXT.includes(ext)) return true
      if (String(file?.mime_type || '').startsWith('image/')) return true
      return file?.result_kind === '胶图'
    },
    isVideo(file) {
      const ext = this.fileExt(file?.original_name).toLowerCase()
      if (VIDEO_EXT.includes(ext)) return true
      return String(file?.mime_type || '').startsWith('video/')
    },
    showTileExt(file) {
      if (this.isVideo(file)) return false
      return !(this.isImage(file) && file.thumb_object_url)
    },
    isTrace(file) {
      return ['ab1', 'abi'].includes(this.fileExt(file?.original_name).toLowerCase())
    },
    isSequence(file) {
      return this.fileExt(file?.original_name).toLowerCase() === 'seq'
    },
    traceDirection(file) {
      const target = String(file?.sequence_target || '')
      if (target === 'i5' || /F$/.test(target)) return 'F'
      if (target === 'i7' || /R$/.test(target)) return 'R'
      const match = String(file?.original_name || '').match(/(?:^|[_-])M13([FR])(?=$|[_.-])/i)
      if (match) return match[1].toUpperCase()
      return ''
    },
    primerLabel(file) {
      return PRIMER_TARGET_LABELS[file?.sequence_target] || ''
    },
    traceTargetSequence(file) {
      const target = String(file?.sequence_target || '')
      const source = this.order.primer_sequences?.[target] || ''
      return assembledCheck(source, this.traceDirection(file))
    },
    packageDirectory(path) {
      const parts = String(path || '').split('/').filter(Boolean)
      return parts.length > 1 ? parts.slice(0, -1).join(' / ') : '包根目录'
    },
    fileDate(file) {
      return String(file?.created_at || '').slice(0, 10) || '—'
    },
    fileSize(bytes) {
      const size = Number(bytes)
      if (!Number.isFinite(size) || size <= 0) return '未知大小'
      if (size < 1024) return `${size} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      return `${(size / (1024 * 1024)).toFixed(1)} MB`
    },
    railSequenceLabel(file) {
      const target = PRIMER_TARGET_LABELS[file?.sequence_target] || file?.sequence_target || '引物'
      if (file?.sequence_status === 'matched') return `${target} 匹配`
      if (file?.sequence_status === 'arm_only') return `${target} 不对`
      if (file?.sequence_status === 'not_found') return `${target} 未匹配`
      return ''
    },
    fileMeta(file) {
      return [
        file.uploaded_by || '未知上传者',
        this.fileSize(file.byte_size),
        this.fileDate(file),
        file.sequence_check,
      ].filter(Boolean).join(' · ')
    },
    setObjectUrl(file, field, key, blob) {
      const previous = file[field]
      if (previous) URL.revokeObjectURL(previous)
      const tracked = this.fileObjectUrls[key]
      if (tracked && tracked !== previous) URL.revokeObjectURL(tracked)
      const url = URL.createObjectURL(blob)
      file[field] = url
      this.fileObjectUrls[key] = url
    },
    revokeObjectUrls() {
      Object.values(this.fileObjectUrls).forEach((url) => URL.revokeObjectURL(url))
      this.fileObjectUrls = {}
    },
    async loadImageThumb(file) {
      if (!this.isImage(file)) return
      const request = this.loadRequest
      try {
        const blob = await fetchFileBlob(libraryFileDownloadUrl(file.id, '&preview=true&thumb=1&w=240&h=160'))
        if (request !== this.loadRequest) return
        const current = this.files.find((item) => item.id === file.id)
        if (current) this.setObjectUrl(current, 'thumb_object_url', `thumb_${file.id}`, blob)
      } catch {
        /* 缩略图失败时用扩展名占位 */
      }
    },
    async loadImageThumbs() {
      await Promise.all(this.gelFiles.map((file) => this.loadImageThumb(file)))
    },
    selectPackage(folder) {
      this.endRegionDrawing()
      this.closeFileRename()
      this.closeRegionRename()
      this.currentFileId = null
      this.packageFocus = null
      this.packagePath = ''
      this.packageSelectedKey = ''
      this.selectedPackage = folder
    },
    goPackagePath(path) {
      this.packagePath = path
      this.packageSelectedKey = ''
      this.packageFocus = null
    },
    selectPackageEntry(entry) {
      if (entry.type === 'folder') {
        this.goPackagePath(entry.path)
        return
      }
      this.packageSelectedKey = entry.key
      this.openPackageFile(entry.file)
    },
    openPackageFile(file) {
      this.packageFocus = file
      this.packageSelectedKey = `file:${file.file_id}`
      this.currentFileId = null
    },
    downloadStored(file) {
      const url = file.link_id
        ? libraryFileDownloadUrl(file.link_id)
        : libraryStoredFileDownloadUrl(file.file_id)
      this.download({ id: file.link_id, original_name: file.original_name }, url)
    },
    selectFile(file) {
      this.selectedPackage = null
      this.packageFocus = null
      this.packagePath = ''
      this.packageSelectedKey = ''
      this.showFile(file)
    },
    showFile(file) {
      if (!file) return
      if (file.id === this.currentFileId) {
        if (this.imagePreviewError) this.loadPreview(file)
        return
      }
      this.endRegionDrawing()
      this.closeFileRename()
      this.closeRegionRename()
      this.currentFileId = file.id
      this.imagePreviewError = ''
      this.imageRect = null
      this.prepareFileView()
      this.loadPreview(file)
    },
    async loadPreview(file) {
      if (!this.isImage(file)) return
      if (file.preview_object_url) {
        this.$nextTick(this.onStageImageLoad)
        return
      }
      const request = this.loadRequest
      this.imagePreviewLoading = true
      this.imagePreviewError = ''
      try {
        const blob = await fetchFileBlob(libraryFileDownloadUrl(file.id, '&preview=true'))
        if (request !== this.loadRequest || this.currentFileId !== file.id) return
        const current = this.files.find((item) => item.id === file.id)
        if (current) this.setObjectUrl(current, 'preview_object_url', `preview_${file.id}`, blob)
      } catch (error) {
        if (request !== this.loadRequest) return
        if (this.currentFileId === file.id) this.imagePreviewError = '图片预览失败'
        notifyApiError(error, { messages: { default: '图片预览失败' } })
      } finally {
        if (request === this.loadRequest && this.currentFileId === file.id) this.imagePreviewLoading = false
      }
    },
    clampZoom(value) {
      return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value))
    },
    resetView() {
      this.view = { zoom: 1, x: 0, y: 0, rotation: 0, brightness: 100, contrast: 100, invert: false }
      this.viewMode = 'fit'
      this.syncRegionOverlay()
    },
    prepareFileView() {
      this.view.zoom = 1
      this.view.x = 0
      this.view.y = 0
      if (this.viewMode !== 'fill') this.viewMode = 'fit'
    },
    onStageImageLoad() {
      if (this.viewMode === 'fill') {
        this.fillView()
        return
      }
      if (this.viewMode === 'fit' && Math.abs(this.view.rotation % 180) === 90) {
        this.fitRotation()
        return
      }
      this.syncRegionOverlay()
    },
    rotateBy(delta) {
      this.view.rotation = ((this.view.rotation + delta) % 360 + 360) % 360
      this.$nextTick(() => {
        if (this.viewMode === 'fill') {
          this.fillView()
          return
        }
        if (this.viewMode === 'fit') {
          this.fitRotation()
          return
        }
        this.syncRegionOverlay()
      })
    },
    fitRotation() {
      const stage = this.$refs.viewerStage
      const image = this.$refs.stageImage
      const quarterTurn = Math.abs(this.view.rotation % 180) === 90
      if (!stage || !image?.offsetWidth || !image?.offsetHeight || !quarterTurn) {
        this.view.zoom = 1
        this.view.x = 0
        this.view.y = 0
        this.syncRegionOverlay()
        return
      }
      const stageRect = stage.getBoundingClientRect()
      const scale = Math.min(
        stageRect.width / image.offsetHeight,
        stageRect.height / image.offsetWidth,
      )
      this.view.zoom = this.clampZoom(Math.min(1, scale))
      this.view.x = 0
      this.view.y = 0
      this.syncRegionOverlay()
    },
    toggleFillView() {
      if (this.viewMode === 'fit') {
        this.fillView()
        return
      }
      this.viewMode = 'fit'
      this.fitRotation()
    },
    fillView() {
      const stage = this.$refs.viewerStage
      const image = this.$refs.stageImage
      if (!stage || !image) return
      const stageRect = stage.getBoundingClientRect()
      const imageRect = image.getBoundingClientRect()
      const baseWidth = imageRect.width / this.view.zoom
      const baseHeight = imageRect.height / this.view.zoom
      if (!baseWidth || !baseHeight) return
      this.view.zoom = this.clampZoom(Math.max(
        stageRect.width / baseWidth,
        stageRect.height / baseHeight,
      ))
      this.view.x = 0
      this.view.y = 0
      this.viewMode = 'fill'
      this.syncRegionOverlay()
    },
    onViewerKeydown(event) {
      if (event.key === 'Escape') {
        if (this.fileRenameOpen) {
          this.closeFileRename()
          return
        }
        if (this.regionRenameIndex !== null) {
          this.closeRegionRename()
          return
        }
        if (this.isFullscreen) this.isFullscreen = false
        return
      }
      const target = event.target
      const isEditing = target?.isContentEditable
        || ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target?.tagName)
      if (
        event.key === 'Enter'
        && this.pendingRegionRenameIndex !== null
        && this.regionRenameIndex === null
        && !isEditing
      ) {
        event.preventDefault()
        this.openRegionRename(this.pendingRegionRenameIndex)
      }
    },
    toggleFullscreen() {
      this.isFullscreen = !this.isFullscreen
      this.syncRegionOverlay()
    },
    enhance() {
      const enabled = !this.isEnhanced
      this.view.brightness = enabled ? 190 : 100
      this.view.contrast = enabled ? 150 : 100
    },
    zoomBy(ratio) {
      this.view.zoom = this.clampZoom(this.view.zoom * ratio)
      if (this.view.zoom === 1) {
        this.view.x = 0
        this.view.y = 0
      }
      this.viewMode = 'custom'
      this.syncRegionOverlay()
    },
    onWheel(event) {
      if (!this.showGelStage) return
      event.preventDefault()
      const rect = event.currentTarget.getBoundingClientRect()
      const anchorX = event.clientX - rect.left - rect.width / 2
      const anchorY = event.clientY - rect.top - rect.height / 2
      const next = this.clampZoom(this.view.zoom * (event.deltaY < 0 ? 1.15 : 1 / 1.15))
      const ratio = next / this.view.zoom
      this.view.x = anchorX - (anchorX - this.view.x) * ratio
      this.view.y = anchorY - (anchorY - this.view.y) * ratio
      this.view.zoom = next
      this.viewMode = 'custom'
      this.syncRegionOverlay()
    },
    onStageMouseDown(event) {
      if (event.button === 0 && event.shiftKey && this.showGelStage && this.canManageFiles) {
        if (this.currentRegions.length >= MAX_QC_REGIONS) {
          ElMessage.warning(`单个文件最多框选 ${MAX_QC_REGIONS} 个区域`)
          return
        }
        if (!this.regionPoint(event)) return
        this.endPan()
        this.regionDrawing = true
        this.regionDraft = null
        this.startRegionSelection(event)
        return
      }
      if (this.regionDrawing) {
        this.startRegionSelection(event)
        return
      }
      this.startPan(event)
    },
    startPan(event) {
      if (!this.showGelStage || event.button !== 0) return
      this.panning = true
      this.panOrigin = { x: event.clientX - this.view.x, y: event.clientY - this.view.y }
      window.addEventListener('mousemove', this.onPan)
      window.addEventListener('mouseup', this.endPan)
    },
    onPan(event) {
      if (!this.panning || !this.panOrigin) return
      const x = event.clientX - this.panOrigin.x
      const y = event.clientY - this.panOrigin.y
      if (x === this.view.x && y === this.view.y) return
      this.viewMode = 'custom'
      this.view.x = x
      this.view.y = y
      this.syncRegionOverlay()
    },
    endPan() {
      if (!this.panning) return
      this.panning = false
      this.panOrigin = null
      window.removeEventListener('mousemove', this.onPan)
      window.removeEventListener('mouseup', this.endPan)
    },
    syncRegionOverlay() {
      this.$nextTick(() => {
        const stage = this.$refs.viewerStage
        const image = this.$refs.stageImage
        if (!stage || !image) {
          this.imageRect = null
          return
        }
        const stageRect = stage.getBoundingClientRect()
        this.imageRect = {
          stageWidth: stageRect.width,
          stageHeight: stageRect.height,
          width: image.offsetWidth,
          height: image.offsetHeight,
        }
      })
    },
    regionOverlayStyle(region) {
      const rect = this.imageRect
      if (!region || !rect?.width || !rect?.height) return {}
      const { zoom, x: panX, y: panY, rotation } = this.view
      const rw = region.width * rect.width
      const rh = region.height * rect.height
      const dx = (region.x + region.width / 2 - 0.5) * rect.width
      const dy = (region.y + region.height / 2 - 0.5) * rect.height
      const rad = (rotation || 0) * Math.PI / 180
      const cos = Math.cos(rad)
      const sin = Math.sin(rad)
      const sx = (dx * cos - dy * sin) * zoom
      const sy = (dx * sin + dy * cos) * zoom
      const swap = Math.abs((rotation || 0) % 180) === 90
      const screenW = (swap ? rh : rw) * zoom
      const screenH = (swap ? rw : rh) * zoom
      return {
        left: `${rect.stageWidth / 2 + panX + sx - screenW / 2}px`,
        top: `${rect.stageHeight / 2 + panY + sy - screenH / 2}px`,
        width: `${screenW}px`,
        height: `${screenH}px`,
      }
    },
    regionLabelBelow(region) {
      return Boolean(region && region.y < 0.08)
    },
    regionPoint(event) {
      const stage = this.$refs.viewerStage
      const image = this.$refs.stageImage
      if (!stage || !image?.offsetWidth || !image?.offsetHeight) return null
      const stageRect = stage.getBoundingClientRect()
      const zoom = this.view.zoom || 1
      const px = (event.clientX - stageRect.left - stageRect.width / 2 - this.view.x) / zoom
      const py = (event.clientY - stageRect.top - stageRect.height / 2 - this.view.y) / zoom
      const rad = -(this.view.rotation || 0) * Math.PI / 180
      const cos = Math.cos(rad)
      const sin = Math.sin(rad)
      const x = ((px * cos - py * sin) + image.offsetWidth / 2) / image.offsetWidth
      const y = ((px * sin + py * cos) + image.offsetHeight / 2) / image.offsetHeight
      if (x < 0 || y < 0 || x > 1 || y > 1) return null
      return { x, y }
    },
    toggleRegionDrawing() {
      if (!this.canManageFiles) return
      if (this.regionDrawing) {
        this.endRegionDrawing()
        return
      }
      if (this.currentRegions.length >= MAX_QC_REGIONS) {
        ElMessage.warning(`单个文件最多框选 ${MAX_QC_REGIONS} 个区域`)
        return
      }
      this.endPan()
      this.regionDrawing = true
      this.regionDraft = null
    },
    startRegionSelection(event) {
      if (event.button !== 0) return
      const point = this.regionPoint(event)
      if (!point) return
      event.preventDefault()
      this.regionStart = point
      this.regionDraft = { x: point.x, y: point.y, width: 0, height: 0 }
      window.addEventListener('mousemove', this.onRegionSelection)
      window.addEventListener('mouseup', this.finishRegionSelection)
    },
    queueRegionDraft(draft) {
      this.pendingRegionDraft = draft
      if (this.regionFrame) return
      this.regionFrame = window.requestAnimationFrame(() => {
        this.regionFrame = 0
        if (!this.pendingRegionDraft) return
        this.regionDraft = this.pendingRegionDraft
        this.pendingRegionDraft = null
      })
    },
    onRegionSelection(event) {
      if (!this.regionStart) return
      const point = this.regionPoint(event)
      if (!point) return
      const x = Math.min(this.regionStart.x, point.x)
      const y = Math.min(this.regionStart.y, point.y)
      this.queueRegionDraft({
        x,
        y,
        width: Math.abs(point.x - this.regionStart.x),
        height: Math.abs(point.y - this.regionStart.y),
      })
    },
    async finishRegionSelection() {
      window.removeEventListener('mousemove', this.onRegionSelection)
      window.removeEventListener('mouseup', this.finishRegionSelection)
      if (this.regionFrame) {
        cancelAnimationFrame(this.regionFrame)
        this.regionFrame = 0
      }
      const region = this.pendingRegionDraft || this.regionDraft
      this.pendingRegionDraft = null
      this.regionStart = null
      if (!region || region.width < 0.01 || region.height < 0.01) {
        this.regionDraft = null
        this.regionDrawing = false
        return
      }
      const file = this.currentFile
      const previous = Array.isArray(file?.qc_regions) ? file.qc_regions.map((item) => ({ ...item })) : []
      const nextRegions = [
        ...previous,
        { ...region, label: this.regionDefaultLabel(previous.length) },
      ]
      if (file) file.qc_regions = nextRegions
      this.regionDraft = null
      this.regionDrawing = false
      const saved = await this.saveFileMetadata({ qc_regions: nextRegions }, '质检区域已保存')
      if (!saved) {
        if (file) file.qc_regions = previous
        return
      }
      this.pendingRegionRenameIndex = previous.length
    },
    endRegionDrawing() {
      window.removeEventListener('mousemove', this.onRegionSelection)
      window.removeEventListener('mouseup', this.finishRegionSelection)
      if (this.regionFrame) {
        cancelAnimationFrame(this.regionFrame)
        this.regionFrame = 0
      }
      this.pendingRegionDraft = null
      this.regionDrawing = false
      this.regionStart = null
      this.regionDraft = null
    },
    regionDefaultLabel(index) {
      return `选区 ${String.fromCharCode(65 + index)}`
    },
    regionDisplayName(region, index) {
      const label = String(region?.label || '').trim()
      return label || this.regionDefaultLabel(index)
    },
    openRegionRename(index) {
      if (!this.canManageFiles) return
      const region = this.currentRegions[index]
      if (!region) return
      this.closeFileRename()
      this.regionRenameIndex = index
      this.regionRenameDraft = this.regionDisplayName(region, index)
      this.pendingRegionRenameIndex = null
    },
    setRegionRenameVisible(index, visible) {
      if (visible) {
        this.openRegionRename(index)
      } else if (this.regionRenameIndex === index) {
        this.closeRegionRename()
      }
    },
    focusRegionRenameInput(index) {
      this.focusAndSelectInput(this.$refs[`regionRenameInput-${index}`])
    },
    focusAndSelectInput(reference) {
      const input = Array.isArray(reference) ? reference[0] : reference
      input?.focus()
      const nativeInput = input?.input || input?.$el?.querySelector('input')
      nativeInput?.select()
    },
    closeRegionRename() {
      this.regionRenameIndex = null
      this.regionRenameDraft = ''
      this.pendingRegionRenameIndex = null
    },
    async saveRegionRename() {
      const index = this.regionRenameIndex
      const label = String(this.regionRenameDraft || '').trim()
      if (index === null || !this.currentRegions[index]) return
      if (!label) {
        ElMessage.warning('请输入标记名称')
        return
      }
      if (label.length > 24) {
        ElMessage.warning('标记名称不能超过 24 个字符')
        return
      }
      const regions = this.currentRegions.map((item, regionIndex) => (
        regionIndex === index
          ? { ...item, label }
          : item
      ))
      const saved = await this.saveFileMetadata({ qc_regions: regions }, '标记名称已更新')
      if (saved) this.closeRegionRename()
    },
    async removeRegion(index) {
      if (!this.canManageFiles) return
      const regions = this.currentRegions.filter((_, regionIndex) => regionIndex !== index)
      const saved = await this.saveFileMetadata(
        { qc_regions: regions.length ? regions : null },
        '质检区域已删除',
      )
      if (saved) this.closeRegionRename()
    },
    async clearRegion() {
      const saved = await this.saveFileMetadata({ qc_regions: null }, '已清除质检区域')
      if (saved) this.closeRegionRename()
    },
    prepareFileRename() {
      if (!this.canManageFiles || !this.currentFile) return
      const currentName = this.currentFile.original_name || ''
      const suffixIndex = currentName.lastIndexOf('.')
      this.fileRenameDraft = this.fileRenameSuffix
        ? currentName.slice(0, suffixIndex)
        : currentName
      this.closeRegionRename()
    },
    focusFileRenameInput() {
      this.focusAndSelectInput(this.$refs.fileRenameInput)
    },
    closeFileRename() {
      this.fileRenameOpen = false
      this.fileRenameDraft = ''
    },
    async saveFileRename() {
      if (!this.currentFile) return
      const baseName = String(this.fileRenameDraft || '').trim()
      if (!baseName) {
        ElMessage.warning('请输入文件名')
        return
      }
      if (/[\\/:*?"<>|]/.test(baseName)) {
        ElMessage.warning('文件名不能包含特殊字符')
        return
      }
      const nextName = `${baseName}${this.fileRenameSuffix}`
      if (nextName.length > 255) {
        ElMessage.warning('文件名不能超过 255 个字符')
        return
      }
      const currentName = this.currentFile.original_name || ''
      if (nextName === currentName) {
        this.closeFileRename()
        return
      }
      const saved = await this.saveFileMetadata({ original_name: nextName }, '文件名已更新')
      if (saved) this.closeFileRename()
    },
    async toggleFinalFile() {
      if (!this.currentFile) return
      const next = !this.currentFile.is_final_qc
      await this.saveFileMetadata(
        { is_final_qc: next },
        next ? '已设为最终，同名的其他文件不再参与质检' : '已取消最终标记',
      )
    },
    async saveFileMetadata(payload, successMessage) {
      if (!this.canManageFiles || !this.currentFile) return false
      const linkId = this.currentFile.id
      const version = (this.fileSaveVersions[linkId] || 0) + 1
      this.fileSaveVersions[linkId] = version
      try {
        const saved = await updateLibraryFile({
          link_id: linkId,
          order_id: this.orderId,
          ...payload,
        })
        if (this.fileSaveVersions[linkId] !== version) return true
        if ('is_final_qc' in payload || 'original_name' in payload) {
          await this.load(saved.id)
        } else {
          const current = this.files.find((item) => item.id === saved.id)
          if (current) Object.assign(current, saved)
          this.currentFileId = saved.id
          this.syncRegionOverlay()
        }
        if (successMessage) ElMessage.success(successMessage)
        return true
      } catch (error) {
        if (this.fileSaveVersions[linkId] !== version) return false
        this.regionDraft = null
        notifyApiError(error, { messages: { default: '保存文件信息失败' } })
        return false
      }
    },
    async download(file, sourceUrl) {
      try {
        await downloadFile(
          sourceUrl || libraryFileDownloadUrl(file.id),
          file.original_name || 'download',
        )
      } catch (error) {
        notifyApiError(error, { messages: { default: '下载失败' } })
      }
    },
    pickQcFiles() {
      if (!this.canManageFiles || this.resultUploading) return
      this.$refs.qcFiles.value = ''
      this.$refs.qcFiles.click()
    },
    pickQcFolder() {
      if (!this.canManageFiles || this.resultUploading) return
      this.$refs.qcFolder.value = ''
      this.$refs.qcFolder.click()
    },
    onQcFiles(event) {
      const files = Array.from(event.target.files || []).map((file) => ({
        file,
        path: file.name,
      }))
      this.uploadDropped(files)
    },
    onQcFolder(event) {
      const files = Array.from(event.target.files || []).map((file) => ({
        file,
        path: String(file.webkitRelativePath || file.name || '').replaceAll('\\', '/'),
      }))
      this.uploadDropped(files)
    },
    async onDropResults(event) {
      try {
        await this.uploadDropped(await readDroppedFiles(event.dataTransfer))
      } catch (error) {
        notifyApiError(error, { messages: { default: '读取文件夹失败' } })
      }
    },
    async uploadDropped(dropped) {
      if (!this.canManageFiles) {
        ElMessage.warning('您没有权限上传结果文件')
        return
      }
      if (!dropped.length) return
      let rows = dropped
      try {
        rows = await expandResultArchives(dropped)
      } catch (error) {
        notifyApiError(error, { messages: { default: '读取压缩包失败' } })
        return
      }
      if (!rows.length) return
      const limitError = resultUploadLimitError(rows)
      if (limitError) {
        ElMessage.warning(limitError)
        return
      }
      if (this.resultUploading) {
        ElMessage.info('上一批文件仍在上传，请稍候')
        return
      }
      const form = new FormData()
      form.append('order_id', String(this.orderId))
      rows.forEach((item) => {
        form.append('files', item.file)
        form.append('paths', item.path)
      })
      this.resultUploading = true
      try {
        const saved = await uploadLibraryFileBatch(form)
        await this.load(this.currentFileId)
        const summary = saved?.summary || []
        const notice = qcUploadNotice(summary)
        ElMessage[notice.type](notice.text)
        const issues = summary.flatMap((item) => (item.issues || []).map((issue) => (
          `${item.name}：${issue.reason} ${issue.count} 个`
        )))
        if (issues.length) ElMessage.warning(issues.join('；'))
      } catch (error) {
        notifyApiError(error, { messages: { default: '上传失败' } })
      } finally {
        this.resultUploading = false
      }
    },
    sortFiles() {
      const finalThenNewest = (left, right) => (
        Number(Boolean(right.is_final_qc)) - Number(Boolean(left.is_final_qc))
        || Number(right.id) - Number(left.id)
      )
      const isRead = (file) => ['AB1', 'ABI', 'SEQ'].includes(this.fileExt(file.original_name))
      const gels = this.files.filter((file) => this.isImage(file)).sort(finalThenNewest)
      const others = this.files.filter((file) => !this.isImage(file) && !isRead(file)).sort(finalThenNewest)
      const buckets = new Map()
      this.files
        .filter((file) => !this.isImage(file) && isRead(file))
        .sort((left, right) => Number(left.id) - Number(right.id))
        .forEach((file) => {
          const name = String(file.original_name || '')
          const stem = name.slice(0, name.lastIndexOf('.')).toLowerCase()
          const key = `${stem}/${file.package_id || ''}`
          if (!buckets.has(key)) buckets.set(key, { stem, traces: [], seqs: [] })
          const bucket = buckets.get(key)
          ;(this.fileExt(name) === 'SEQ' ? bucket.seqs : bucket.traces).push(file)
        })
      const pairs = [...buckets.values()].flatMap(({ stem, traces, seqs }) => (
        Array.from({ length: Math.max(traces.length, seqs.length) }, (_, index) => {
          const group = [traces[index], seqs[index]].filter(Boolean)
          return {
            stem,
            group,
            final: group.some((file) => file.is_final_qc),
            newest: Math.max(...group.map((file) => Number(file.id))),
          }
        })
      ))
      pairs.sort((left, right) => (
        left.stem.localeCompare(right.stem, 'zh-CN', { numeric: true })
        || Number(right.final) - Number(left.final)
        || right.newest - left.newest
      ))
      this.files = [...gels, ...pairs.flatMap((item) => item.group), ...others]
    },
    async confirmDelete(message, confirmButtonText = '删除') {
      if (!this.canManageFiles) {
        ElMessage.warning('您没有权限删除结果文件')
        return false
      }
      try {
        await ElMessageBox.confirm(message, '删除确认', { type: 'warning', confirmButtonText })
        return true
      } catch {
        return false
      }
    },
    async removePackage(folder) {
      const shared = folder.shared
        ? '该包还关联其他工单，本次只从当前工单移除，原始包会保留。'
        : '这是最后一个工单关联，原始包和包内文件也会删除。'
      if (!await this.confirmDelete(`移除测序包 ${folder.name}？${shared}`, '移除')) return
      try {
        const result = await deleteLibraryResult({
          order_id: this.orderId,
          package_id: folder.id,
        })
        ElMessage.success(result?.package_deleted ? '测序包已删除' : '已从当前工单移除')
        await this.load()
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除失败' } })
      }
    },
    async deleteStoredFile(file) {
      const message = `删除 ${file.original_name}？文件会从测序包里去掉，并取消它和所有工单的关联。`
      if (!await this.confirmDelete(message)) return
      try {
        await deleteLibraryResult({ file_id: file.file_id, order_id: this.orderId })
        ElMessage.success('已删除')
        await this.load()
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除失败' } })
      }
    },
    async removeFile(file) {
      const shared = Number(file.linked_order_count || 1) > 1
      const message = file.package_id
        ? `取消 ${file.original_name} 与当前工单的关联？文件仍留在测序包里。`
        : shared
          ? `${file.original_name} 还挂在其他工单上。本次只会从当前工单移除，其他工单不受影响。`
          : `确认删除 ${file.original_name}？这是最后一个引用，磁盘文件也会删除。`
      if (!await this.confirmDelete(message)) return
      const index = this.files.findIndex((item) => item.id === file.id)
      const neighbor = this.files[index + 1] || this.files[index - 1]
      try {
        await deleteLibraryResult({ link_id: file.id, order_id: this.orderId })
        ElMessage.success(file.package_id ? '已取消关联' : '已删除')
        await this.load(neighbor?.id)
      } catch (error) {
        notifyApiError(error, { messages: { default: '删除失败' } })
      }
    },
    async persist(field) {
      const qcConclusion = ['qc_result', 'qc_owner', 'qc_on', 'qc_note'].includes(field)
      if (!(qcConclusion ? this.canEditQc : this.canEdit) || !this.order?.id) return
      this.order[field] = persistValue(this.order[field])
      const qcFields = field === 'qc_result'
        ? stampQcFields(this.order, getSerumUserName(useUserStore().userInfo))
        : []
      if (this.sameValue(this.baseline[field], this.order[field]) && !qcFields.length) return
      const payload = { id: this.order.id, [field]: this.order[field] }
      qcFields.forEach((key) => {
        payload[key] = this.order[key]
      })
      if (field === 'target_codes') payload.target_name = this.order.target_name
      try {
        const saved = await saveLibraryOrder(payload)
        this.order = { ...this.order, ...saved }
        if (!Array.isArray(this.order.target_codes)) this.order.target_codes = []
        if (!Array.isArray(this.order.plate_nos)) this.order.plate_nos = []
        this.plateDraft = plateNumbersText(this.order.plate_nos)
        this.baseline = JSON.parse(JSON.stringify(this.order))
      } catch (error) {
        this.order[field] = this.baseline[field]
        qcFields.forEach((key) => {
          this.order[key] = this.baseline[key]
        })
        if (field === 'target_codes') this.order.target_name = this.baseline.target_name
        if (field === 'plate_nos') this.plateDraft = plateNumbersText(this.order.plate_nos)
        notifyApiError(error, { messages: { default: '保存失败' } })
        return
      }
      if (PRIMER_RESULT_FIELDS.includes(field)) await this.load(this.currentFileId)
    },
    updateStatus(value) {
      this.order.status = value
      this.persist('status')
    },
    updatePriority(value) {
      this.order.priority = value
      this.persist('priority')
    },
    onTargetChange(payload) {
      this.order.target_codes = payload.codes
      this.order.target_name = payload.name
      this.persist('target_codes')
    },
    openSourceDiscovery(discoveryId) {
      const id = String(discoveryId || '').trim()
      if (!id) return
      rememberDiscoveryFocus(id)
      this.$router.push({ name: 'DiscoveryWorkbench' })
    },
    onPlateDraftInput(value) {
      if (!this.canEdit) return
      this.plateDraft = normalizePlateInputText(value)
      this.order.plate_nos = plateNumbersFromText(this.plateDraft)
    },
  },
}
</script>

<style scoped>
.library-detail {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: var(--list-page-gap);
  height: calc(100vh - 96px);
  min-height: 640px;
  padding: var(--list-page-padding);
  overflow: hidden;
  background: var(--list-page-bg);
}

/* ---------- 工单概览 ---------- */

.detail-overview {
  flex: none;
  overflow: hidden;
  background: var(--list-surface-bg);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.detail-topbar {
  display: flex;
  flex: none;
  gap: 14px;
  align-items: center;
  min-height: 68px;
  padding: 10px 18px;
  background: #fff;
  border-bottom: 1px solid #edf0f4;
}

.back-button {
  flex: none;
  height: 32px;
  padding: 0 14px 0 2px;
  color: var(--el-text-color-regular);
  border-right: 1px solid #e4e9f0;
  border-radius: 0;
}

.back-button:hover {
  color: var(--el-color-primary);
  background: transparent;
}

.topbar-identity {
  display: flex;
  flex: 0 1 300px;
  flex-direction: column;
  min-width: 150px;
}

.detail-title {
  max-width: 300px;
  margin: 0;
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: var(--list-page-title-size);
  font-weight: var(--list-page-title-weight);
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-code {
  max-width: 360px;
  margin-top: 4px;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: var(--list-page-subtitle-size);
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topbar-state {
  display: flex;
  flex: none;
  gap: 6px;
  align-items: center;
}

.topbar-meta {
  display: flex;
  gap: 22px;
  margin: 0 0 0 auto;
  min-width: 0;
}

.topbar-meta div {
  min-width: 0;
}

.topbar-meta dt {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.topbar-meta dd {
  margin: 2px 0 0;
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qc-gaps {
  display: flex;
  flex: none;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
  max-width: 280px;
}

.qc-gaps span {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  min-height: 26px;
  padding: 3px 10px;
  font-size: 12px;
  line-height: 18px;
  border: 1px solid transparent;
  border-radius: 999px;
}

.qc-gaps i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.qc-gaps .is-warn {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-7);
}

.qc-gaps .is-warn i {
  background: var(--el-color-warning);
}

.qc-gaps .is-fail {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-7);
}

.qc-gaps .is-fail i {
  background: var(--el-color-danger);
}

.save-hint {
  display: inline-flex;
  flex: none;
  gap: 6px;
  align-items: center;
  min-height: 26px;
  padding: 3px 10px;
  color: #27815a;
  font-size: 12px;
  background: #edf9f3;
  border: 1px solid #d2f0df;
  border-radius: 999px;
}

.save-hint i {
  width: 6px;
  height: 6px;
  background: #36b37e;
  border-radius: 50%;
}

.save-hint.is-readonly {
  color: var(--el-text-color-secondary);
  background: #f4f6f8;
  border-color: #e6e9ed;
}

.save-hint.is-readonly i {
  background: #9ca3af;
}

/* ---------- 样品来源条 ---------- */

.sample-strip {
  display: flex;
  flex: none;
  gap: 16px;
  align-items: center;
  min-height: 54px;
  padding: 8px 18px;
  background: #fafbfd;
}

.strip-label {
  flex: none;
  padding-right: 16px;
  border-right: 1px solid #e4e9f0;
}

.strip-label strong {
  display: block;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.strip-facts {
  display: grid;
  flex: 1;
  grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
  gap: 4px 18px;
  margin: 0;
  min-width: 0;
}

.strip-fact {
  min-width: 0;
}

.strip-fact dt {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.strip-fact dd {
  margin: 1px 0 0;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------- 结果判读 ---------- */

.viewer-panel {
  display: flex;
  flex-direction: column;
  container-type: inline-size;
  min-width: 0;
  overflow: hidden;
  background: var(--list-surface-bg);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.viewer-caption {
  display: flex;
  flex: none;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  min-height: 50px;
  padding: 8px 16px;
  border-bottom: 1px solid #eef0f4;
}

.caption-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.caption-copy strong {
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.caption-copy span {
  margin-top: 2px;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.caption-actions {
  position: relative;
  z-index: 5;
  display: flex;
  flex: none;
  gap: 6px;
}

.rename-popover-content {
  display: grid;
  gap: 8px;
  color: var(--el-text-color-primary);
}

.rename-popover-content > strong {
  font-size: 13px;
  font-weight: 600;
}

.rename-popover-content > small {
  color: var(--el-text-color-secondary);
  font-size: 10px;
}

.rename-popover-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.viewer-tools {
  display: flex;
  flex: none;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  min-height: 44px;
  padding: 6px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #eef0f4;
}

.image-adjustments {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 7px 12px;
  align-items: center;
  min-width: 0;
}

.tool-slider {
  display: flex;
  gap: 4px;
  align-items: center;
  min-width: 0;
}

.tool-slider span {
  flex: none;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.tool-slider :deep(.el-slider) {
  width: clamp(64px, 7vw, 92px);
  --el-slider-button-size: 18px;
}

.tool-slider b {
  flex: none;
  width: 30px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.tool-buttons {
  display: flex;
  flex: none;
  gap: 4px;
  align-items: center;
}

.tool-actions {
  display: flex;
  flex: none;
  gap: 4px;
  align-items: center;
  padding-left: 9px;
  border-left: 1px solid #e4e8ee;
}

.tool-buttons button,
.tool-reset,
.viewport-tools button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 26px;
  padding: 0 8px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #dfe4ea;
  border-radius: var(--list-inner-radius);
  transition: color 0.16s ease, border-color 0.16s ease;
}

.tool-buttons button:hover,
.tool-reset:hover,
.viewport-tools button:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-5);
}

.tool-buttons button.is-on {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.tool-buttons button:disabled {
  color: var(--el-text-color-disabled);
  cursor: not-allowed;
  background: var(--el-fill-color-light);
  border-color: var(--el-border-color-lighter);
}

.tool-reset {
  flex: none;
  padding: 0 7px;
  border-color: transparent;
  background: transparent;
}

.viewer-stage {
  position: relative;
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 0;
  overflow: hidden;
  background: #f5f7f9;
}

.viewer-panel.is-dark .viewer-stage {
  background:
    radial-gradient(circle at 50% 42%, #1c242e, #0b0f14 72%);
  cursor: grab;
}

.viewer-panel.is-dark .viewer-stage.is-grabbing {
  cursor: grabbing;
}

.viewer-panel.is-dark .viewer-stage.is-selecting {
  cursor: crosshair;
}

.stage-image {
  max-width: 100%;
  max-height: 100%;
  user-select: none;
  will-change: transform;
}

.qc-region-overlay {
  position: absolute;
  z-index: 2;
  box-sizing: border-box;
  pointer-events: none;
  background: transparent;
  border: 2px solid #3b96f2;
  border-radius: 2px;
}

.qc-region-overlay.is-drawing {
  border-style: dashed;
}

.qc-region-label {
  position: absolute;
  top: -23px;
  left: -2px;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  pointer-events: auto;
  background: #3b96f2;
  border: 1px solid #358bdf;
  border-radius: 3px;
  overflow: hidden;
}

.qc-region-label button {
  height: 19px;
  padding: 0 5px;
  color: #fff;
  font-size: 10px;
  line-height: 1;
  cursor: pointer;
  background: transparent;
  border: 0;
}

.qc-region-label button:hover {
  background: #358bdf;
}

.qc-region-label .qc-region-remove {
  padding: 0 5px 1px 3px;
  color: rgb(255 255 255 / 82%);
}

.qc-region-overlay.is-drawing .qc-region-label {
  cursor: default;
  pointer-events: none;
}

.qc-region-overlay.is-label-below .qc-region-label {
  top: calc(100% + 5px);
}

.stage-package {
  display: flex;
  flex-direction: column;
  align-self: stretch;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 16px 18px 18px;
  overflow: hidden;
  text-align: left;
  background: var(--el-fill-color-lighter);
}

.package-browser-head {
  display: flex;
  flex: none;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 10px;
}

.package-browser-head strong,
.package-file strong,
.package-preview-head strong {
  display: block;
}

.package-browser-head span,
.package-file span,
.package-file small,
.package-preview-head small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.package-explorer {
  display: grid;
  grid-template-columns: minmax(360px, 0.95fr) minmax(380px, 1.05fr);
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
}

.package-browser-pane,
.package-preview-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.package-browser-pane {
  border-right: 1px solid var(--el-border-color-lighter);
}

.package-breadcrumb {
  display: flex;
  flex: none;
  gap: 5px;
  align-items: center;
  min-height: 42px;
  padding: 7px 10px;
  overflow-x: auto;
  white-space: nowrap;
  background: var(--el-fill-color-extra-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.package-breadcrumb button {
  padding: 3px 5px;
  color: var(--el-color-primary);
  font-size: 12px;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 4px;
}

.package-breadcrumb button:hover {
  background: var(--el-color-primary-light-9);
}

.package-list-head,
.package-file {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) 64px 72px 76px;
  gap: 8px;
  align-items: center;
}

.package-list-head {
  flex: none;
  padding: 7px 12px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.package-file-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.package-file {
  width: 100%;
  padding: 8px 12px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.package-entry-name {
  display: flex;
  gap: 7px;
  align-items: center;
  min-width: 0;
}

.package-entry-name .el-icon {
  flex: none;
  color: #8b97a8;
  font-size: 17px;
}

.package-entry-name .el-icon.is-excel { color: #217346; }
.package-entry-name .el-icon.is-word { color: #2b579a; }
.package-entry-name .el-icon.is-ppt { color: #d24726; }
.package-entry-name .el-icon.is-pdf { color: #b30b00; }
.package-entry-name .el-icon.is-zip { color: #7d6b58; }
.package-entry-name .el-icon.is-trace { color: #6f42c1; }
.package-entry-name .el-icon.is-sequence { color: #52627f; }
.package-entry-name .el-icon.is-text { color: #637083; }
.package-entry-name .el-icon.is-video { color: #3d6f8f; }

.package-file strong,
.package-file span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.package-file:hover {
  background: var(--el-fill-color-extra-light);
}

.package-file.is-active {
  position: relative;
  z-index: 1;
  background: var(--el-color-primary-light-9);
  box-shadow: inset 3px 0 var(--el-color-primary);
}

.package-folder-empty {
  padding: 36px 16px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  text-align: center;
}

.package-preview-empty {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
}

.package-preview-empty .el-icon {
  font-size: 38px;
}

.package-preview-head {
  display: flex;
  flex: none;
  gap: 12px;
  align-items: start;
  justify-content: space-between;
  min-height: 64px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.package-preview-head > div {
  min-width: 0;
}

.package-preview-actions {
  display: flex;
  flex: none;
  gap: 8px;
}

.package-preview-head strong,
.package-preview-head small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.package-preview-body {
  flex: 1;
  min-height: 0;
  padding: 0;
  overflow: hidden;
  background: var(--el-fill-color-extra-light);
}

.stage-document-preview {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

.stage-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 400px;
  padding: 32px;
  text-align: center;
}

.stage-empty .el-icon {
  margin-bottom: 12px;
  color: #a7bdd3;
  font-size: 40px;
}

.stage-empty strong {
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.stage-empty p {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.7;
}

.viewer-footer {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
  padding: 5px 10px;
  background: #fff;
  border-top: 1px solid #e8ebef;
}

.viewer-gesture-hint {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewport-tools {
  display: flex;
  flex: none;
  gap: 4px;
  align-items: center;
  margin-left: 12px;
}

.viewport-tools .fill-button {
  min-width: 64px;
}

.viewport-tools b {
  width: 42px;
  color: var(--el-text-color-regular);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  text-align: center;
}

.tool-separator {
  width: 1px;
  height: 16px;
  margin: 0 3px;
  background: #e4e7eb;
}

.viewer-panel.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1990;
  width: 100vw;
  height: 100vh;
  background: #fff;
  border: 0;
}

/* ---------- 右侧信息 ---------- */

.metric-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
  margin: 0 0 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #eef0f4;
}

.metric-list div {
  min-width: 0;
}

.metric-list dt {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-list dd {
  margin: 2px 0 0;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------- 表单通用 ---------- */

.field-grid {
  display: grid;
}

/* ---------- 自适应 ---------- */

@media (max-width: 1440px) {
  .topbar-meta div:last-child {
    display: none;
  }
}

@media (max-width: 1180px) {
  .library-detail {
    height: auto;
    min-height: calc(100vh - 96px);
    overflow: visible;
  }

  .viewer-panel {
    min-height: 520px;
  }
}

@media (max-width: 820px) {
  .detail-topbar {
    flex-wrap: wrap;
  }

  .topbar-meta {
    margin-left: 0;
  }

  .sample-strip {
    flex-wrap: wrap;
  }

  .strip-label {
    padding-right: 0;
    border-right: 0;
  }

}

/* ---------- 文件 / 画布 / 信息三栏审阅台 ---------- */

.review-workspace {
  display: grid;
  flex: 1;
  grid-template-columns: 216px minmax(0, 1fr) 352px;
  gap: 10px;
  min-height: 0;
  overflow: hidden;
}

.file-rail {
  min-width: 0;
  min-height: 0;
  padding: 0 14px 14px;
  overflow-y: auto;
  background: var(--list-mid-bg);
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
  scrollbar-gutter: stable;
}

.rail-heading,
.inspector-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 50px;
}

.rail-heading {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--list-mid-bg);
}

.rail-heading strong,
.inspector-heading strong {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.rail-heading .rail-count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.file-tile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 7px;
  align-items: start;
}

.qc-folder-input {
  display: none;
}

.file-upload-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 122px;
  padding: 10px;
  cursor: pointer;
  background: var(--el-color-primary-light-9);
  border: 1px dashed var(--el-color-primary-light-5);
  border-radius: var(--list-chip-radius);
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.file-upload-tile:hover {
  background: var(--el-color-primary-light-8);
  border-color: var(--el-color-primary);
}

.file-upload-tile.is-disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.file-upload-tile .el-icon {
  margin-bottom: 5px;
  color: var(--el-color-primary);
  font-size: 22px;
}

.file-upload-tile strong {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.file-upload-tile span {
  margin-top: 3px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.file-tile {
  position: relative;
  display: grid;
  grid-template-rows: auto auto auto;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 2px 9px;
  align-items: center;
  width: 100%;
  min-width: 0;
  min-height: 62px;
  padding: 7px 9px 7px 7px;
  overflow: hidden;
  color: inherit;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e1e6ec;
  border-radius: var(--list-chip-radius);
  transition: transform 0.16s ease;
}

.file-tile:hover {
  transform: translateX(4px);
}

.file-tile.is-active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.file-tile.is-final {
  padding-right: 42px;
}

.file-tile.is-replaced {
  opacity: 0.5;
}

.tile-final {
  position: absolute;
  top: 7px;
  right: 7px;
  padding: 1px 5px;
  color: #27815a;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  background: #edf9f3;
  border-radius: 999px;
}

.file-tile:focus-visible,
.inspector-tabs button:focus-visible,
.tool-buttons button:focus-visible,
.tool-reset:focus-visible,
.viewport-tools button:focus-visible {
  outline: 2px solid var(--el-color-primary-light-5);
  outline-offset: 1px;
}

.tile-visual {
  position: relative;
  display: flex;
  grid-row: 1 / -1;
  grid-column: 1;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 46px;
  overflow: hidden;
  color: #728196;
  background: #edf1f5;
  border-radius: var(--list-inner-radius);
}

.tile-visual :deep(.el-image) {
  width: 100%;
  height: 100%;
}

.tile-file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
  font-size: 22px;
}

.tile-file-icon.is-excel { color: #217346; }
.tile-file-icon.is-word { color: #2b579a; }
.tile-file-icon.is-ppt { color: #d24726; }
.tile-file-icon.is-pdf { color: #b30b00; }
.tile-file-icon.is-zip { color: #7d6b58; }
.tile-file-icon.is-trace { color: #6f42c1; }
.tile-file-icon.is-sequence { color: #5b6b8c; }
.tile-file-icon.is-text { color: #637083; }
.tile-file-icon.is-video { color: #3d6f8f; }

.tile-ext-badge {
  position: absolute;
  bottom: 2px;
  left: 2px;
  max-width: calc(100% - 4px);
  padding: 0 3px;
  overflow: hidden;
  color: #fff;
  font: 600 8px/13px Arial, sans-serif;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #7f8a99;
  border-radius: 3px;
}

.tile-ext-badge.is-excel { background: #217346; }
.tile-ext-badge.is-word { background: #2b579a; }
.tile-ext-badge.is-ppt { background: #d24726; }
.tile-ext-badge.is-pdf { background: #b30b00; }
.tile-ext-badge.is-zip { background: #c8841c; }
.tile-ext-badge.is-trace { background: #6f42c1; }
.tile-ext-badge.is-sequence { background: #52627f; }
.tile-ext-badge.is-text { background: #637083; }
.tile-ext-badge.is-video { background: #3d6f8f; }

.tile-name {
  align-self: end;
  margin: 0;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-tile small {
  align-self: start;
  margin: 0;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-tile small.tile-check {
  color: var(--el-color-primary);
}

.file-tile small.tile-check.is-matched {
  color: var(--el-color-success);
}

.file-tile small.tile-check.is-unmatched {
  color: var(--el-color-danger);
}

.record-inspector {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #f7f9fb;
  border: var(--list-surface-border);
  border-radius: var(--list-surface-radius);
  box-shadow: var(--list-surface-shadow);
}

.inspector-heading {
  flex: none;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e9edf2;
}

.inspector-tabs {
  display: flex;
  flex: none;
  gap: 0;
  min-height: 42px;
  padding: 0 8px;
  overflow-x: auto;
  background: #fff;
  border-bottom: 1px solid #e7ebf0;
}

.inspector-tabs button {
  flex: 1 0 auto;
  min-width: 50px;
  height: 42px;
  padding: 0 9px;
  color: var(--el-text-color-regular);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  transition: color 0.16s ease, border-color 0.16s ease;
}

.inspector-tabs button:hover {
  color: var(--el-color-primary);
}

.inspector-tabs button.is-active {
  color: var(--el-color-primary);
  font-weight: 600;
  border-bottom-color: var(--el-color-primary);
}

.inspector-scroll {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.section-heading {
  display: flex;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 10px;
  margin-bottom: 13px;
  border-bottom: 1px solid #e9edf2;
}

.section-heading strong {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.record-inspector .field-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.record-inspector .inspector-form :deep(.el-form-item) {
  display: block;
  min-width: 0;
  margin: 0;
}

.record-inspector .inspector-form :deep(.el-form-item.is-wide) {
  grid-column: 1 / -1;
}

.record-inspector .field-row-break {
  grid-column: 2;
}

.record-inspector .inspector-form :deep(.el-form-item__label) {
  display: block;
  height: auto;
  padding: 0;
  margin-bottom: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.3;
  text-align: left;
}

.record-inspector .inspector-form :deep(.el-form-item__content) {
  min-width: 0;
  line-height: normal;
}

.primer-matrix {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) minmax(0, 1fr) 54px;
  gap: 6px;
  align-items: center;
  width: 100%;
}

.primer-matrix-heading {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 10px;
  line-height: 18px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.primer-chain {
  color: var(--el-text-color-regular);
  font-size: 12px;
  text-align: center;
}

.record-inspector .inspector-form :deep(.el-input),
.record-inspector .inspector-form :deep(.el-select),
.record-inspector .inspector-form :deep(.el-date-editor) {
  width: 100%;
  --el-date-editor-width: 100%;
}

.record-inspector .inspector-form :deep(.el-input__wrapper),
.record-inspector .inspector-form :deep(.el-select__wrapper) {
  min-height: 32px;
  background: #fff;
  box-shadow: 0 0 0 1px #dfe4ea inset;
  transition: box-shadow 0.16s ease, background-color 0.16s ease;
}

.record-inspector .inspector-form :deep(.el-input__wrapper:hover),
.record-inspector .inspector-form :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--el-color-primary-light-5) inset;
}

.record-inspector .inspector-form :deep(.is-focus .el-input__wrapper),
.record-inspector .inspector-form :deep(.el-input__wrapper.is-focus),
.record-inspector .inspector-form :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

.record-inspector .inspector-form :deep(.is-disabled .el-input__wrapper),
.record-inspector .inspector-form :deep(.el-select__wrapper.is-disabled) {
  background: #f5f7f9;
  box-shadow: 0 0 0 1px #e7eaee inset;
}

.inspector-section {
  padding: 14px;
  background: #fff;
  border-radius: var(--list-mid-radius);
  animation: inspector-section-enter 0.16s ease-out;
}

.inspector-form .inspector-section + .inspector-section {
  margin-top: 12px;
}

@keyframes inspector-section-enter {
  from {
    opacity: 0;
    transform: translateY(3px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.source-link.is-link,
.source-link.is-link :deep(.el-input__wrapper),
.source-link.is-link :deep(.el-input__inner),
.source-link.is-link :deep(.el-input__suffix) {
  cursor: pointer;
}

.source-link-action {
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 600;
}

.catalog-sequence {
  float: right;
  margin-left: 16px;
  color: var(--el-text-color-secondary);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
}

@media (max-width: 1440px) {
  .review-workspace {
    grid-template-columns: 196px minmax(0, 1fr) 336px;
  }
}

@container (max-width: 760px) {
  .package-explorer {
    grid-template-rows: minmax(220px, 0.9fr) minmax(240px, 1.1fr);
    grid-template-columns: minmax(0, 1fr);
  }

  .package-browser-pane {
    border-right: 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }
}

@media (max-width: 1180px) {
  .review-workspace {
    min-height: 620px;
    grid-template-columns: 184px minmax(0, 1fr) 320px;
  }

  .package-explorer {
    grid-template-rows: minmax(220px, 0.9fr) minmax(240px, 1.1fr);
    grid-template-columns: minmax(0, 1fr);
  }

  .package-browser-pane {
    border-right: 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }
}

@media (max-width: 900px) {
  .review-workspace {
    display: flex;
    flex-direction: column;
    overflow: visible;
  }

  .file-rail {
    display: flex;
    flex: 0 0 126px;
    gap: 8px;
    padding: 8px 10px;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .rail-heading {
    flex: 0 0 62px;
    height: auto;
  }

  .file-tile-grid {
    display: flex;
  }

  .file-upload-tile {
    flex: 0 0 108px;
    width: 108px;
    height: 108px;
  }

  .file-tile {
    flex: 0 0 180px;
    width: 180px;
    height: 108px;
  }

  .review-workspace > .viewer-panel {
    min-height: 520px;
  }

  .record-inspector {
    min-height: 560px;
  }

  .record-inspector .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .record-inspector .field-row-break {
    display: none;
  }

  .record-inspector .inspector-form :deep(.el-form-item.is-wide) {
    grid-column: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .file-tile,
  .file-upload-tile,
  .inspector-tabs button,
  .inspector-section {
    animation: none;
    transition: none;
  }
}
</style>
