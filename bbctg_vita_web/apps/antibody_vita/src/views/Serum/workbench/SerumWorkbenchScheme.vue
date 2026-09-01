<template>
  <div class="workbench-scheme-page" v-loading="loading">
    <el-card class="box-card basic-info-card" :body-style="{ padding: '18px' }">
      <template #header>
        <div class="clearfix">
          <span>1. 方案草稿</span>
          <span class="header-hint">核对抗原 / 小鼠 / 步骤后再开展；开展前不写入免疫实验主表</span>
          <div style="float: right;">
              <span v-if="!canEdit" class="readonly-hint">只读</span>
              <span v-if="autoSaving" style="margin-right: 10px; color: #409EFF; font-size: 12px;">
                  <el-icon class="is-loading"><Loading /></el-icon> 自动保存中...
              </span>
              <el-button size="small" type="primary" @click="submitForm" :loading="loading" :disabled="loading || autoSaving || !canEdit">保存</el-button>
              <el-button
                v-if="canStart"
                size="small"
                type="success"
                @click="handleStart"
                :loading="loading"
                :disabled="loading || autoSaving"
              >
                开展
              </el-button>
              <el-button size="small" @click="handleCancel">返回工作台</el-button>
          </div>
        </div>
      </template>

      <el-form :model="postForm" label-width="100px">
        <!-- Row 1: 项目编号, 实验ID, 负责人 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="项目编号">
              <el-input v-model="postForm.project_code" placeholder="可选，开展前必填" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="实验ID">
              <el-input v-model="postForm.experiment_id" disabled placeholder="首次保存自动生成" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="负责人">
              <SerumUserSelect
                v-model="postForm.owner"
                placeholder="选择负责人"
                :options="schemeUserOptions('owner')"
                :disabled="!canEdit"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Row 2: 靶点名称, 靶点类型, 靶点大小 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="靶点名称">
              <el-select
                ref="targetSelect"
                v-model="postForm.target_codes"
                filterable
                multiple
                remote
                remote-show-suffix
                class="target-name-select"
                :remote-method="searchTargetOptions"
                :loading="targetLoading"
                :placeholder="postForm.target_name ? '' : '搜索并选择靶点'"
                title="Shift+Enter 可直接录入未入库靶点名称"
                style="width: 100%"
                :disabled="!canEdit"
                @change="handleTargetChange"
                @focus="handleTargetFocus"
                @keydown.shift.enter.capture.prevent.stop="commitFreeTargetName"
              >
                <template #tag>
                  <span class="target-selected-text">{{ postForm.target_name }}</span>
                </template>
                <el-option
                  v-for="item in targetOptions"
                  :key="item.snum"
                  :label="item.name"
                  :value="item.snum"
                >
                  <div
                    v-if="targetAliasEdit?.code === item.snum"
                    class="target-option target-option--editing"
                    @click.stop
                    @mousedown.stop
                  >
                    <span class="target-option__name">{{ item.name }}</span>
                    <el-input
                      ref="targetAliasInput"
                      v-model="targetAliasEdit.name"
                      size="small"
                      placeholder="输入自定义名称"
                      @blur="targetAliasEdit = null"
                      @keydown.enter.prevent.stop="confirmTargetAlias"
                      @keydown.esc.prevent.stop="targetAliasEdit = null"
                    />
                  </div>
                  <div
                    v-else
                    class="target-option"
                    title="右键可自定义项目中的显示名称"
                    @contextmenu.prevent.stop="startTargetAliasEdit(item)"
                  >
                    <span class="target-option__name">{{ item.name }}</span>
                    <span
                      v-if="targetDisplayNames[item.snum] && targetDisplayNames[item.snum] !== item.name"
                      class="target-option__alias"
                    >
                      当前名称：{{ targetDisplayNames[item.snum] }}
                    </span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="靶点类型">
              <el-select v-model="postForm.target_type" style="width:100%" filterable allow-create default-first-option placeholder="选择或输入靶点类型" :disabled="!canEdit">
                <el-option label="I型" value="I型" />
                <el-option label="II型" value="II型" />
                <el-option label="III型" value="III型" />
                <el-option label="分泌" value="分泌" />
                <el-option label="多穿" value="多穿" />
                <el-option label="胞内" value="胞内" />
                <el-option label="小分子" value="小分子" />
                <el-option label="GPI" value="GPI" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="靶点大小">
              <el-select v-model="postForm.target_size" style="width:100%" filterable allow-create default-first-option placeholder="选择或输入靶点大小" :disabled="!canEdit">
                <el-option label="大于300AA" value="大于300AA" />
                <el-option label="小于300AA" value="小于300AA" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Row 3: 项目名称, 课题类型, 产品经理 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="项目名称">
              <el-input v-model="postForm.project_name" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="课题类型">
              <el-select v-model="postForm.study_type" style="width:100%" filterable allow-create default-first-option placeholder="选择或输入课题类型" :disabled="!canEdit">
                <el-option label="数据包" value="数据包" />
                <el-option label="客户关注" value="客户关注" />
                <el-option label="公司内部研发" value="公司内部研发" />
                <el-option label="公司重点" value="公司重点" />
                <el-option label="客户付钱" value="客户付钱" />
                <el-option label="PCC过会" value="PCC过会" />
                <el-option label="沈博关注" value="沈博关注" />
                <el-option label="大客户关注" value="大客户关注" />
                <el-option label="我也布吉岛" value="我也布吉岛" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="产品经理">
              <SerumUserSelect
                v-model="postForm.pm"
                placeholder="选择产品经理"
                :options="schemeUserOptions('pm')"
                :disabled="!canEdit"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Row 4: 开始日期, 检测方法, 项目状态 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="开始日期">
              <el-date-picker v-model="postForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" :disabled="!canEdit" @change="recalculateAllStepDates" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检测方法">
              <AssayMethodEditor
                v-model:assay-method="postForm.assay_method"
                v-model:facs-plate-count="postForm.facs_plate_count"
                v-model:elisa-plate-count="postForm.elisa_plate_count"
                :disabled="!canEdit"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目状态">
              <el-select v-model="postForm.project_status" style="width:100%" disabled>
                <el-option v-for="item in schemeProjectStatusOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Row 5: 免疫间隔, 备注 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="免疫间隔">
              <el-input v-model="postForm.immunization_interval" placeholder="天数" :disabled="!canEdit" @change="recalculateAllStepDates">
                <template #append>天</template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="实验备注">
              <el-input v-model="postForm.remark" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Row 6: 项目目的 -->
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="项目目的">
              <el-input v-model="postForm.project_purpose" type="textarea" :rows="2" placeholder="请输入项目目的" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <div
      class="scheme-detail-editor"
      :class="{ 'is-readonly': !canEdit }"
      :inert="!canEdit"
    >
      <!-- 2. Antigens (Full Width) -->
      <el-card class="box-card" :body-style="{ padding: '15px' }">
        <template #header>
          <div class="clearfix small-header">
            <span>2. 抗原信息 (Antigens)</span>
                <el-button v-if="canEdit" style="float: right; padding: 3px 0" link @click="addAntigen">添加抗原</el-button>
          </div>
        </template>
        <el-table :data="postForm.antigens" border size="small" style="width: 100%">
            <!-- Hidden IDs -->
            <el-table-column label="抗原ID" width="60">
                <template #default="{ row }">
                    <el-input v-model="row.antigen_id" size="small" disabled />
                </template>
            </el-table-column>
            <el-table-column label="抗原名称" min-width="150">
                    <template #default="{ row }">
                    <el-input v-model="row.antigen_name" size="small" placeholder="必填" @paste="handleAntigenPaste($event, row)" />
                </template>
            </el-table-column>
            <el-table-column label="抗原种属" width="100">
                <template #default="{ row }">
                    <el-select v-model="row.species" size="small" filterable allow-create default-first-option placeholder="" style="width:100%">
                        <el-option label="人" value="人" />
                        <el-option label="猴" value="猴" />
                        <el-option label="鼠" value="鼠" />
                        <el-option label="狗" value="狗" />
                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="抗原类型" width="100">
                <template #default="{ row }">
                    <el-select v-model="row.antigen_type" size="small" filterable allow-create default-first-option placeholder="" style="width:100%" @change="handleAntigenTypeChange(row)">
                        <el-option label="四聚体" value="四聚体" />
                        <el-option label="细胞" value="细胞" />
                        <el-option label="DNA" value="DNA" />
                        <el-option label="LNP" value="LNP" />
                        <el-option label="VLP" value="VLP" />
                        <el-option label="FC" value="FC" />
                        <el-option label="His" value="His" />
                        <el-option label="NoTag" value="NoTag" />
                        <el-option label="OVA" value="OVA" />
                        <el-option label="KLH" value="KLH" />
                        <el-option label="BSA" value="BSA" />
                        <el-option label="SMA" value="SMA" />


                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="货号">
                <template #default="{ row }">
                    <el-input v-model="row.catalog_no" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="批号">
                <template #default="{ row }">
                    <el-input v-model="row.lot_no" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="原液浓度">
                <template #default="{ row }">
                    <el-input v-model="row.stock_conc" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="供应商">
                <template #default="{ row }">
                    <el-input v-model="row.vendor" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="佐剂类型" width="120">
                <template #default="{ row }">
                    <el-select v-model="row.adjuvant_type" size="small" filterable allow-create default-first-option style="width:100%" placeholder="选择佐剂" @change="handleAntigenAdjuvantTypeChange(row)">
                        <el-option label="弗氏佐剂" value="弗氏佐剂" />
                        <el-option label="ADDAVAX" value="ADDAVAX" />
                        <el-option label="无" value="无" />
                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="佐剂来源" width="100">
                <template #default="{ row }">
                    <el-select v-model="row.adjuvant_source" size="small" filterable allow-create default-first-option style="width:100%" placeholder="选择来源">
                        <el-option label="进口" value="进口" />
                        <el-option label="国产" value="国产" />
                        <el-option label="自制" value="自制" />
                        <el-option label="无" value="无" />
                    </el-select>
                </template>
            </el-table-column>
                <el-table-column v-if="canEdit" label="操作" width="50" align="center">
                <template #default="{ $index }">
                    <el-icon class="delete-btn" @click="removeAntigen($index)"><Delete /></el-icon>
                </template>
            </el-table-column>
        </el-table>
    </el-card>

    <!-- 3. Mouse Groups (Full Width) -->
    <el-card class="box-card" :body-style="{ padding: '15px' }">
        <template #header>
          <div class="clearfix small-header">
            <span>3. 小鼠分组 (Mouse Groups)</span>
            <el-button v-if="canEdit" style="float: right; padding: 3px 0" link @click="addMouseGroup">添加分组</el-button>
          </div>
        </template>
        <el-table :data="postForm.mouse_groups" border size="small" style="width: 100%">
            <el-table-column label="组别" min-width="80">
                <template #default="{ row }">
                    <el-select v-model="row.group_id" size="small" filterable allow-create default-first-option style="width:100%" placeholder="选择组别" @focus="cacheGroupId(row)" @change="handleGroupIdChange(row, $event)">
                        <el-option label="G1" value="G1" />
                        <el-option label="G2" value="G2" />
                        <el-option label="G3" value="G3" />
                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="小鼠名称/品系" min-width="120">
                    <template #default="{ row }">
                    <el-input v-model="row.mouse_strain" size="small" @change="updateProjectName" />
                </template>
            </el-table-column>
            <el-table-column label="归类鼠型" min-width="120">
                    <template #default="{ row }">
                    <el-select v-model="row.mouse_strain_category" size="small" filterable allow-create default-first-option style="width:100%" placeholder>
                        <el-option
                          v-for="item in mouseStrainCategoryOptions"
                          :key="item"
                          :label="item"
                          :value="item"
                        />
                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="免疫数量" min-width="80">
                    <template #default="{ row }">
                    <el-input v-model="row.mouse_count" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="周龄" min-width="80">
                <template #default="{ row }">
                    <el-input v-model="row.age_weeks" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="性别" min-width="80">
                <template #default="{ row }">
                    <el-select v-model="row.sex" size="small" filterable allow-create default-first-option style="width:100%" placeholder="选择性别">
                        <el-option label="F/M" value="F/M" />
                        <el-option label="F" value="F" />
                        <el-option label="M" value="M" />
                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="笼位" min-width="120">
                <template #default="{ row }">
                    <el-input v-model="row.cage_position" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="供应商" min-width="120">
                <template #default="{ row }">
                    <el-input v-model="row.vendor" size="small" />
                </template>
            </el-table-column>
            <el-table-column label="鼠号列表" min-width="160">
                <template #default="{ row }">
                    <el-tooltip
                      :content="row.mouse_no_list || ''"
                      placement="top"
                      :show-after="300"
                      :disabled="!(row.mouse_no_list || '').trim()"
                    >
                      <el-input
                        :model-value="row.mouse_no_list"
                        readonly
                        placeholder="点击编辑鼠号"
                        size="small"
                        class="mouse-no-list-input"
                        @click="openMouseRegistryDialog(row)"
                      />
                    </el-tooltip>
                </template>
            </el-table-column>
            <el-table-column label="备注" min-width="100">
                <template #default="{ row }">
                    <el-input v-model="row.remark" size="small" />
                </template>
            </el-table-column>
                <el-table-column v-if="canEdit" label="操作" width="50" align="center">
                <template #default="{ $index }">
                    <el-icon class="delete-btn" @click="removeMouseGroup($index)"><Delete /></el-icon>
                </template>
            </el-table-column>
        </el-table>
    </el-card>

    <!-- 4. Immunization Scheme -->
    <el-card class="box-card" :body-style="{ padding: '15px' }">
      <template #header>
        <div class="clearfix small-header">
          <span>4. 免疫方案 (Immunization Scheme)</span>
          <el-button v-if="canEdit && postForm.mouse_groups.length > 0" style="float: right; padding: 3px 0" link @click="addStepToGroup(activeGroupTab)">添加步骤</el-button>
        </div>
      </template>

      <div v-if="postForm.mouse_groups.length === 0" style="text-align: center; color: #999; padding: 20px;">
          请先在上方添加小鼠分组
      </div>

      <div v-else>
        <el-tabs v-model="activeGroupTab" type="card">
            <el-tab-pane
              v-for="(group, idx) in postForm.mouse_groups.filter(g => g.group_id)"
              :key="group.group_id || `tmp-${idx}`"
              :name="group.group_id">
              <template #label>
                <span
                  @contextmenu.prevent="openCopyDialogFromTab(group.group_id)"
                  title="右键复制免疫方案"
                >
                  分组 {{ group.group_id }}
                </span>
              </template>

              <el-table :data="getStepsForGroup(group.group_id)" border size="small" style="width:100%">
                <el-table-column label="阶段" min-width="92">
                     <template #default="{ row }">
                        <el-select v-model="row.stage_name" size="small" filterable allow-create default-first-option placeholder="" style="width:100%" @change="handleStageChange(row)">
                            <el-option label="一免" value="一免" />
                            <el-option label="二免" value="二免" />
                            <el-option label="三免" value="三免" />
                            <el-option label="四免" value="四免" />
                            <el-option label="五免" value="五免" />
                            <el-option label="六免" value="六免" />
                            <el-option label="七免" value="七免" />
                            <el-option label="八免" value="八免" />
                            <el-option label="九免" value="九免" />
                            <el-option label="十免" value="十免" />
                            <el-option label="采血" value="采血" />
                            <el-option label="冲击" value="冲击" />
                        </el-select>
                    </template>
                </el-table-column>
                <el-table-column label="计划日期" min-width="150">
                     <template #default="{ row }">
                        <el-date-picker v-model="row.date_actual" type="date" value-format="YYYY-MM-DD" size="small" style="width: 100%;" @change="handleStepDateChange(row)" />
                    </template>
                </el-table-column>
                <el-table-column label="相对天数" min-width="70">
                     <template #default="{ row }">
                        <el-input v-model="row.day_relative" size="small" placeholder="" />
                    </template>
                </el-table-column>
                <el-table-column label="抗原" min-width="150">
                     <template #default="{ row, $index }">
                        <div class="antigen-select-wrapper">
                            <div
                              class="antigen-display-text"
                              :class="{ 'is-placeholder': !getAntigenDisplay(row.antigen_id) }"
                            >{{ getAntigenDisplay(row.antigen_id) || '选择抗原' }}</div>
                            <el-select
                                :ref="`antigenSelect_${group.group_id}_${$index}`"
                                v-model="row.antigen_id"
                                size="small"
                                placeholder="选择抗原"
                                filterable
                                multiple
                                class="antigen-select-hidden"
                                @change="handleAntigenChange(row, group.group_id, $index)"
                            >
                                 <el-option v-for="a in postForm.antigens" :key="a.antigen_id" :label="a.antigen_name" :value="a.antigen_id" />
                                 <el-option label="N/A(不适用)" value="N/A" />
                            </el-select>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column label="剂量" min-width="90">
                     <template #default="{ row }">
                        <el-input v-model="row.antigen_dose" size="small" />
                    </template>
                </el-table-column>
                <el-table-column label="佐剂" min-width="90">
                     <template #default="{ row }">
                        <el-input v-model="row.adjuvant_name" size="small" />
                    </template>
                </el-table-column>
                <el-table-column label="CPG剂量" min-width="90">
                     <template #default="{ row }">
                        <el-input v-model="row.cpg_dose" size="small" />
                    </template>
                </el-table-column>
                <el-table-column label="注射体积" min-width="90">
                     <template #default="{ row }">
                        <el-input v-model="row.injection_volume" size="small" />
                    </template>
                </el-table-column>
                <el-table-column label="途径" min-width="90">
                     <template #default="{ row }">
                        <el-select v-model="row.route" size="small" filterable allow-create default-first-option style="width:100%" @change="handleRouteChange(row)">
                            <el-option label="s.c." value="s.c." />
                            <el-option label="i.p." value="i.p." />
                            <el-option label="i.v." value="i.v." />
                            <el-option label="i.m." value="i.m." />
                            <el-option label="DNA" value="DNA" />
                        </el-select>
                    </template>
                </el-table-column>
                <el-table-column label="注射部位" min-width="122">
                     <template #default="{ row }">
                        <el-input v-model="row.injection_site" size="small" />
                    </template>
                </el-table-column>
                <el-table-column label="备注" min-width="50" align="center">
                     <template #default="{ row }">
                        <el-tooltip :content="row.remark || '暂无备注'" placement="top" :disabled="!row.remark">
                            <el-icon
                                class="remark-icon"
                                :class="{'has-remark': row.remark}"
                                @click="openRemarkDialog(row)"
                                style="cursor: pointer; font-size: 17px;">
                              <Edit />
                            </el-icon>
                        </el-tooltip>
                    </template>
                </el-table-column>
                <el-table-column v-if="canEdit" label="操作" min-width="50" align="center">
                    <template #default="{ row }">
                        <el-icon class="delete-btn" @click="removeStep(row)"><Delete /></el-icon>
                    </template>
                </el-table-column>
             </el-table>

          </el-tab-pane>
       </el-tabs>
      </div>

      <!-- Remark Dialog -->
      <el-dialog title="编辑备注" v-model="remarkDialogVisible" width="500px">
        <el-input
          v-model="currentRemark"
          type="textarea"
          :rows="6"
          placeholder="请输入备注信息"
          maxlength="500"
          show-word-limit>
        </el-input>
        <template #footer>
          <span class="dialog-footer">
          <el-button @click="remarkDialogVisible = false">取 消</el-button>
          <el-button type="primary" @click="saveRemark">确 定</el-button>
          </span>
        </template>
      </el-dialog>

      <el-dialog title="复制免疫方案" v-model="copyDialogVisible" width="500px" class="copy-dialog">
        <template #header>
          <span class="copy-dialog-title">复制免疫方案</span>
        </template>
        <el-form label-width="85px">
          <el-form-item label="来源分组">
            <el-input :value="copyFromGroup" disabled style="background-color: #f5f7fa;" />
          </el-form-item>

          <el-form-item label="目标分组">
            <el-select v-model="copyToGroups" multiple style="width:100%" placeholder="请选择目标分组（可多选）">
              <el-option
                v-for="g in postForm.mouse_groups.filter(g => g.group_id)"
                :key="g.group_id"
                :label="g.group_id"
                :value="g.group_id"
                :disabled="g.group_id === copyFromGroup"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="复制选项" class="copy-options-item">
            <div style="display: flex; align-items: center; width: 100%;">
              <el-checkbox v-model="overwriteSteps">覆盖目标已有步骤</el-checkbox>
              <div style="flex: 1; text-align: right;">
                <el-button @click="copyDialogVisible = false" style="margin-right: 10px;">取消</el-button>
                <el-button type="primary" @click="doCopyScheme">确定复制</el-button>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </el-dialog>
    </el-card>



    <!-- 5. Titer Section -->
    <el-card class="box-card" :body-style="{ padding: '15px' }">
        <template #header>
          <div class="clearfix small-header">
              <span>5. 效价检测 (Titer Assay)</span>
          </div>
        </template>
        <el-row :gutter="20">
            <el-col :span="24" style="margin-bottom: 20px;">
                <div class="sub-header">
                    <span>检测标靶</span>
                    <el-button v-if="canEdit" link @click="addTarget">
                      <el-icon><Plus /></el-icon>
                    </el-button>
                </div>
                 <el-table :data="postForm.titer_targets" border size="small">
                    <el-table-column label="名称" min-width="150">
                        <template #default="{ row }">
                            <el-input v-model="row.name" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column label="类型" min-width="75">
                        <template #default="{ row }">
                            <el-select v-model="row.type" size="small" filterable allow-create default-first-option placeholder=" " style="width:100%">
                                <el-option label="细胞" value="细胞" />
                                <el-option label="蛋白" value="蛋白" />
                            </el-select>
                        </template>
                    </el-table-column>
                    <el-table-column label="种属" min-width="75">
                        <template #default="{ row }">
                            <el-select v-model="row.species" size="small" placeholder=" " style="width:100%">
                                <el-option label="人" value="人" />
                                <el-option label="猴" value="猴" />
                                <el-option label="鼠" value="鼠" />
                                <el-option label="狗" value="狗" />
                                <el-option label="猫" value="猫" />
                                <el-option label="空白" value="空白" />
                            </el-select>
                        </template>
                    </el-table-column>
                    <el-table-column label="批次" min-width="100">
                        <template #default="{ row }">
                            <el-input v-model="row.batch_no" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column label="代次" min-width="100">
                        <template #default="{ row }">
                            <el-input v-model="row.passage" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column label="细胞量" min-width="100">
                        <template #default="{ row }">
                            <el-input v-model="row.cell_count" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column label="货号" min-width="100">
                        <template #default="{ row }">
                            <el-input v-model="row.catalog_no" size="small" />
                        </template>
                    </el-table-column>
                     <el-table-column label="来源" min-width="100">
                        <template #default="{ row }">
                            <el-input v-model="row.source" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column v-if="canEdit" width="50" align="center">
                        <template #default="{ $index }">
                            <el-icon class="delete-btn" @click="removeTarget($index)"><Delete /></el-icon>
                        </template>
                    </el-table-column>
                </el-table>
            </el-col>

            <el-col :span="24">
                 <div class="sub-header">
                    <span>阳性对照</span>
                    <el-button v-if="canEdit" link @click="addPC">
                      <el-icon><Plus /></el-icon>
                    </el-button>
                </div>
                 <el-table :data="postForm.titer_pcs" border size="small">
                    <el-table-column label="PC名称">
                        <template #default="{ row }">
                            <el-input v-model="row.pc_name" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column label="货号/批次">
                        <template #default="{ row }">
                            <el-input v-model="row.catalog_batch" size="small" />
                        </template>
                    </el-table-column>
                     <el-table-column label="来源">
                        <template #default="{ row }">
                            <el-input v-model="row.source" size="small" />
                        </template>
                    </el-table-column>
                    <el-table-column label="浓度">
                        <template #default="{ row }">
                            <el-input v-model="row.concentration" size="small" />
                        </template>
                    </el-table-column>
                     <el-table-column v-if="canEdit" width="50" align="center">
                        <template #default="{ $index }">
                            <el-icon class="delete-btn" @click="removePC($index)"><Delete /></el-icon>
                        </template>
                    </el-table-column>
                </el-table>
            </el-col>
        </el-row>
    </el-card>

    <MouseRegistryDialog
      v-model="mouseRegistryDialogVisible"
      :group="mouseRegistryEditingRow"
      @confirm="onMouseRegistryConfirm"
    />
    </div>

  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'

import {
  Delete,
  Edit,
  Loading,
  Plus,
} from '@element-plus/icons-vue'

import {
  ElButton,
  ElCard,
  ElCheckbox,
  ElCol,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElNotification,
  ElOption,
  ElRow,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTooltip,
} from 'element-plus'

import { extractApiError, notifyApiError } from '#/api/errors'
import { fetchSerumTargetOptions } from '#/api/serum'
import {
  fetchWorkbenchDetail,
  fetchWorkbenchOptions,
  saveWorkbenchScheme,
  startWorkbench,
} from '#/api/serumWorkbench'
import { SERUM_ERRORS } from '../shared/errors'
import MouseRegistryDialog from '../shared/MouseRegistryDialog.vue'
import AssayMethodEditor from '../shared/AssayMethodEditor.vue'
import SerumUserSelect from '../shared/SerumUserSelect.vue'
import {
  canAccessSerumDetail,
  canEditSerumProject,
  canEditWorkbench,
  canEditWorkbenchDraft,
  canOpenSerumEdit,
  hasSerumProjectEditPermission,
} from '#/utils/serumPermission'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS } from '#/utils/serumMouseOptions'
import {
  isWorkbenchPlanClosed,
  SERUM_PROJECT_STATUS_DEFAULT,
} from '#/utils/serumProjectStatus'

const MIAN_NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
const SCHEME_PROJECT_STATUS_OPTIONS = [SERUM_PROJECT_STATUS_DEFAULT]
const SCHEME_HEADER_FIELDS = [
  'project_code',
  'project_name',
  'project_purpose',
  'start_date',
  'immunization_interval',
  'target_codes',
  'target_name',
  'target_type',
  'target_size',
  'owner',
  'pm',
  'study_type',
  'assay_method',
  'facs_plate_count',
  'elisa_plate_count',
  'remark',
]
const SCHEME_CHILD_FIELDS = [
  'mouse_groups',
  'antigens',
  'steps',
  'titer_targets',
  'titer_pcs',
]

function createEmptySchemeForm() {
  return {
    id: undefined,
    experiment_id: '',
    project_code: '',
    project_name: '',
    project_purpose: '',
    owner: '',
    start_date: '',
    project_status: SCHEME_PROJECT_STATUS_OPTIONS[0],
    target_codes: [],
    target_name: '',
    target_type: '',
    target_size: '',
    pm: '纪鑫',
    study_type: '',
    assay_method: '',
    facs_plate_count: null,
    elisa_plate_count: null,
    immunization_interval: '',
    remark: '',
    mouse_strain: '',
    mouse_strain_category: '',
    plan_status: '',
    scheme_revision: '',
    mouse_groups: [],
    steps: [],
    antigens: [],
    titer_targets: [],
    titer_pcs: [],
  }
}

function mianNumber(stageName) {
  const name = (stageName || '').trim()
  const idx = MIAN_NUMERALS.findIndex((n) => name === `${n}免`)
  return idx >= 0 ? idx + 1 : null
}

function isMianStage(stageName) {
  return mianNumber(stageName) !== null
}

function mianStageName(n) {
  if (n < 1 || n > 10) return ''
  return `${MIAN_NUMERALS[n - 1]}免`
}

function pickStepsForGroup(steps, groupId) {
  if (!steps || !groupId) return []
  return steps
    .filter((s) => s.group_id === groupId)
    .slice()
    .sort((a, b) => {
      const orderDiff = (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0)
      if (orderDiff !== 0) return orderDiff
      const aid = Number(a.step_id)
      const bid = Number(b.step_id)
      if (Number.isFinite(aid) && Number.isFinite(bid) && aid !== bid) return aid - bid
      return 0
    })
}

function reindexGroupSortOrder(steps, groupId) {
  pickStepsForGroup(steps, groupId).forEach((step, index) => {
    step.sort_order = index
  })
}

function nextAppendStage(groupSteps) {
  const names = groupSteps.map((s) => (s.stage_name || '').trim())
  const mianNums = names.map((name) => mianNumber(name)).filter((n) => n !== null)
  const maxMian = mianNums.length ? Math.max(...mianNums) : 0

  if (maxMian === 0) return '一免'

  const readyForBlood =
    maxMian === 4 &&
    !names.includes('采血') &&
    [1, 2, 3, 4].every((n) => mianNums.includes(n))
  if (readyForBlood) return '采血'

  if (maxMian >= 10) return ''

  return mianStageName(maxMian + 1)
}

function resortMianStepsInGroup(steps, groupId) {
  const ordered = pickStepsForGroup(steps, groupId)
  const sortedMian = ordered
    .filter((s) => isMianStage(s.stage_name))
    .sort((a, b) => (mianNumber(a.stage_name) || 0) - (mianNumber(b.stage_name) || 0))

  let mianIdx = 0
  const rearranged = ordered.map((step) => {
    if (!isMianStage(step.stage_name)) return step
    return sortedMian[mianIdx++] ?? step
  })

  rearranged.forEach((step, index) => {
    step.sort_order = index
  })
}

export default {
  name: 'SerumWorkbenchScheme',
  components: {
    MouseRegistryDialog,
    SerumUserSelect,
    AssayMethodEditor,
    ElButton,
    ElCard,
    ElCheckbox,
    ElCol,
    ElDatePicker,
    ElDialog,
    ElForm,
    ElFormItem,
    ElIcon,
    ElInput,
    Delete,
    Edit,
    Loading,
    Plus,
    ElOption,
    ElRow,
    ElSelect,
    ElTabPane,
    ElTable,
    ElTableColumn,
    ElTabs,
    ElTooltip,
  },
  setup() {
    const userStore = useUserStore()

    return {
      userStore,
    }
  },
  data() {
    return {
      postForm: createEmptySchemeForm(),
      loading: false,
      targetAliasEdit: null,
      targetDisplayNames: {},
      targetLoading: false,
      targetOptions: [],
      targetRequestToken: 0,
      usedUserOptions: { owner: [], pm: [] },
      schemeProjectStatusOptions: SCHEME_PROJECT_STATUS_OPTIONS,
      mouseStrainCategoryOptions: SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS,
      remarkDialogVisible: false,
      currentRemark: '',
      currentRemarkRow: null,
      copyDialogVisible: false,
      copyFromGroup: '',
      copyToGroups: [],
      overwriteSteps: true,
      mouseRegistryDialogVisible: false,
      mouseRegistryEditingRow: null,
      activeGroupTab: null,
      groupIdSnapshots: new WeakMap(),
      autoSaveTimer: null,
      autoSaving: false,
      initializing: true,
      applyingServerState: false,
      initRequestToken: 0,
      loadingWorkbenchId: null,
      activeWorkbenchId: null,
      formRevision: 0,
      savedRevision: 0,
      saveQueued: false,
      savePromise: null,
    }
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {}
    },
    canFullEdit() {
      return canEditWorkbench(this.currentUserInfo)
    },
    canDraftEdit() {
      return canEditWorkbenchDraft(this.currentUserInfo)
    },
    canEdit() {
      return Boolean(this.activeWorkbenchId)
        && (
          this.canFullEdit
          || (this.canDraftEdit && String(this.postForm.plan_status || '草稿').trim() === '草稿')
        )
        && !this.postForm.aligned_locked
    },
    canStart() {
      return this.canFullEdit
        && Boolean(this.activeWorkbenchId)
        && !this.postForm.aligned_locked
        && !isWorkbenchPlanClosed(this.postForm.plan_status)
        && hasSerumProjectEditPermission(this.currentUserInfo)
    },
  },
  watch: {
    postForm: {
      handler() {
        if (this.initializing || this.applyingServerState) return
        this.formRevision += 1
        this.triggerAutoSave()
      },
      deep: true
    }
  },
  created() {
    this.loadWorkbenchOptions()
    const id = this.$route.query.id
    this.initPage(id)
  },
  activated() {
    if (!this.isWorkbenchSchemeRoute(this.$route)) return
    const id = this.parseWorkbenchId(this.$route.query.id)
    if (!id || this.loadingWorkbenchId === id) return
    if (id !== this.activeWorkbenchId) {
      this.initPage(id)
    }
  },
  deactivated() {
    this.clearAutoSaveTimer()
  },
  beforeUnmount() {
    this.clearAutoSaveTimer()
    this.initRequestToken += 1
    this.targetRequestToken += 1
    this.activeWorkbenchId = null
  },
  beforeRouteUpdate(to, from, next) {
    const workbenchId = this.parseWorkbenchId(to.query.id)
    const continueNavigation = () => {
      this.initRequestToken += 1
      this.targetRequestToken += 1
      this.activeWorkbenchId = null
      next()
      this.$nextTick(() => this.initPage(workbenchId, to))
    }
    this.flushPendingSave()
      .then(continueNavigation)
      .catch((err) => {
        this.handleSaveFailure(err)
        next(false)
      })
  },
  beforeRouteLeave(to, from, next) {
    this.flushPendingSave()
      .then(() => {
        this.initRequestToken += 1
        this.targetRequestToken += 1
        this.activeWorkbenchId = null
        next()
      })
      .catch((err) => {
        this.handleSaveFailure(err)
        next(false)
      })
  },
  methods: {
    resetTransientEditors() {
      this.targetAliasEdit = null
      this.remarkDialogVisible = false
      this.currentRemark = ''
      this.currentRemarkRow = null
      this.copyDialogVisible = false
      this.copyFromGroup = ''
      this.copyToGroups = []
      this.mouseRegistryDialogVisible = false
      this.mouseRegistryEditingRow = null
    },
    async loadWorkbenchOptions() {
      try {
        const data = await fetchWorkbenchOptions()
        this.usedUserOptions.owner = this.uniq(data?.owners || [])
        this.usedUserOptions.pm = this.uniq(data?.pms || [])
      } catch {
        // 选项接口不可用时仍可显示当前记录中的人员
      }
    },
    uniq(values) {
      return [...new Set((values || []).map((item) => String(item || '').trim()).filter(Boolean))]
    },
    schemeUserOptions(field) {
      return this.uniq([...(this.usedUserOptions[field] || []), this.postForm[field]])
    },
    isWorkbenchSchemeRoute(route = this.$route) {
      return route?.name === 'SerumWorkbenchScheme'
        || route?.path === '/serum/workbench/scheme'
    },
    parseWorkbenchId(raw) {
      const text = String(raw ?? '').trim()
      if (!/^\d+$/.test(text)) return null
      const value = Number(text)
      return Number.isSafeInteger(value) && value > 0 ? value : null
    },
    async initPage(rawWorkbenchId, route = this.$route) {
      if (!this.isWorkbenchSchemeRoute(route)) return
      const workbenchId = this.parseWorkbenchId(rawWorkbenchId)
      if (!workbenchId) {
        ElMessage.warning('缺少工作台记录')
        this.$router.replace('/serum/workbench')
        return
      }
      if (this.loadingWorkbenchId === workbenchId) return

      const previousWorkbenchId = this.activeWorkbenchId
      const requestToken = ++this.initRequestToken
      this.loadingWorkbenchId = workbenchId
      this.activeWorkbenchId = null
      this.loading = true
      this.initializing = true
      this.clearAutoSaveTimer()
      if (previousWorkbenchId !== workbenchId) {
        this.resetTransientEditors()
        this.postForm = createEmptySchemeForm()
        this.targetDisplayNames = {}
        this.targetOptions = []
        this.targetRequestToken += 1
        this.targetLoading = false
        this.activeGroupTab = null
        this.formRevision = 0
        this.savedRevision = 0
        this.saveQueued = false
      }
      try {
        const detail = await fetchWorkbenchDetail(workbenchId)
        if (
          requestToken !== this.initRequestToken
          || !this.isWorkbenchSchemeRoute(this.$route)
          || this.parseWorkbenchId(this.$route.query.id) !== workbenchId
        ) {
          return
        }
        if (detail?.aligned_locked && detail.serum_project_id) {
          if (canOpenSerumEdit(this.currentUserInfo, detail)) {
            this.$router.replace({ path: '/serum/edit', query: { id: detail.serum_project_id } })
            return
          }
          if (canAccessSerumDetail(this.currentUserInfo)) {
            this.$router.replace({ path: '/serum/detail', query: { id: detail.serum_project_id } })
            return
          }
        }
        const targetCodes = Array.isArray(detail.target_codes) ? detail.target_codes : []
        this.resetTransientEditors()
        this.postForm = {
          ...createEmptySchemeForm(),
          ...detail,
          target_codes: targetCodes,
          mouse_groups: detail.mouse_groups || [],
          antigens: detail.antigens || [],
          steps: detail.steps || [],
          titer_targets: detail.titer_targets || [],
          titer_pcs: detail.titer_pcs || [],
        }
        if (
          !this.postForm.aligned_locked
          && (
            this.canFullEdit
            || (this.canDraftEdit && String(this.postForm.plan_status || '草稿').trim() === '草稿')
          )
        ) {
          this.ensureInitialMouseGroup()
        }
        this.activeWorkbenchId = workbenchId
        this.formRevision = 0
        this.savedRevision = 0
        this.saveQueued = false
        const targetNames = String(detail.target_name || '').split(/[&,]/)
        this.targetDisplayNames = Object.fromEntries(
          targetCodes.map((snum, index) => [snum, targetNames[index] || snum]),
        )
        this.targetOptions = targetCodes.map((snum, index) => ({
          name: targetNames[index] || snum,
          snum,
        }))
        if (targetCodes.length) {
          this.searchTargetOptions('')
        }
        if (this.postForm.steps) {
          this.postForm.steps.forEach((step) => {
            if (step.antigen_id && typeof step.antigen_id === 'string') {
              step.antigen_id = step.antigen_id
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean)
            }
          })
        }
        this.activeGroupTab = this.postForm.mouse_groups[0]?.group_id || null
      } catch (err) {
        if (requestToken === this.initRequestToken) {
          notifyApiError(err, { messages: SERUM_ERRORS.workbench.schemeLoad })
        }
      } finally {
        if (requestToken === this.initRequestToken) {
          this.loading = false
          this.loadingWorkbenchId = null
          this.$nextTick(() => {
            if (requestToken !== this.initRequestToken) return
            this.initializing = false
          })
        }
      }
    },
    async searchTargetOptions(keyword) {
      const requestToken = ++this.targetRequestToken
      this.targetLoading = true
      try {
        const response = await fetchSerumTargetOptions(keyword, this.postForm.target_codes)
        if (requestToken !== this.targetRequestToken) return
        this.targetOptions = response?.items || []
      } catch {
        // 无靶点库权限时仍可用 Shift+Enter 录入名称
      } finally {
        if (requestToken === this.targetRequestToken) this.targetLoading = false
      }
    },
    handleTargetFocus() {
      if (!this.targetOptions.length) {
        this.searchTargetOptions('')
      }
    },
    commitFreeTargetName(event) {
      const input = event.target
      const customName = (input?.value || '').trim()
      if (!customName) return
      this.postForm.target_codes = []
      this.targetDisplayNames = {}
      this.postForm.target_name = customName
      if (input) input.value = ''
      this.updateProjectName()
      this.$nextTick(() => this.$refs.targetSelect?.blur())
    },
    handleTargetChange(codes) {
      const selected = codes || []
      const namesByCode = new Map(this.targetOptions.map((item) => [item.snum, item.name]))
      this.targetDisplayNames = Object.fromEntries(
        selected.map((code) => [
          code,
          this.targetDisplayNames[code] || namesByCode.get(code) || code,
        ]),
      )
      this.postForm.target_name = selected
        .map((code) => this.targetDisplayNames[code] || code)
        .join('&')
      this.updateProjectName()
      this.$nextTick(() => this.$refs.targetSelect?.blur())
    },
    startTargetAliasEdit(item) {
      this.targetAliasEdit = {
        code: item.snum,
        name: this.targetDisplayNames[item.snum] || item.name,
      }
      this.$nextTick(() => {
        const input = Array.isArray(this.$refs.targetAliasInput)
          ? this.$refs.targetAliasInput[0]
          : this.$refs.targetAliasInput
        input?.focus()
        input?.select()
      })
    },
    confirmTargetAlias() {
      if (!this.targetAliasEdit) return
      const { code, name } = this.targetAliasEdit
      const customName = name.trim()
      if (!customName) {
        ElMessage.warning('请输入自定义名称')
        return
      }
      if (/[&,，]/.test(customName)) {
        ElMessage.warning('自定义名称不能包含 & 或逗号')
        return
      }
      this.targetDisplayNames = {
        ...this.targetDisplayNames,
        [code]: customName,
      }
      if (!this.postForm.target_codes.includes(code)) {
        this.postForm.target_codes = [...this.postForm.target_codes, code]
      }
      this.targetAliasEdit = null
      this.handleTargetChange(this.postForm.target_codes)
    },
    getAntigenDisplay(antigenIds) {
      const ids = Array.isArray(antigenIds) ? antigenIds : []
      if (!ids.length) return ''

      const names = ids.map(id => {
        const trimmedId = String(id).trim()
        const antigen = this.postForm.antigens && this.postForm.antigens.find(a => String(a.antigen_id) === trimmedId)
        return antigen ? antigen.antigen_name : trimmedId
      })

      return names.join(' + ')
    },
    getStepsForGroup(groupId) {
        return pickStepsForGroup(this.postForm.steps, groupId)
    },
    addStepToGroup(groupId) {
        if (!this.canEdit) return
        if (!groupId) {
            ElMessage.warning('请先选择一个分组')
            return
        }

        const groupSteps = this.getStepsForGroup(groupId)
        const nextStageName = nextAppendStage(groupSteps)

        const newStep = {
            group_id: groupId,
            sort_order: groupSteps.length,
            stage_name: nextStageName,
            day_relative: '',
            date_actual: '',
            antigen_id: [],
            antigen_dose: '',
            adjuvant_name: '',
            cpg_dose: '20µg',
            injection_volume: '100µL',
            route: 's.c.',
            injection_site: '颈部+尾根部',
            remark: ''
        }

        if (nextStageName === '采血') {
            newStep.antigen_id = ['N/A']
            newStep.antigen_dose = '-'
            newStep.adjuvant_name = '-'
            newStep.cpg_dose = '-'
            newStep.injection_volume = '-'
            newStep.route = '-'
            newStep.injection_site = '-'
        }

        this.postForm.steps.push(newStep)
        reindexGroupSortOrder(this.postForm.steps, groupId)
        this.recalculateGroupDates(groupId, groupSteps.length)
    },
    openRemarkDialog(row) {
        this.currentRemarkRow = row
        this.currentRemark = row.remark || ''
        this.remarkDialogVisible = true
    },
    saveRemark() {
        if (this.currentRemarkRow) {
            this.currentRemarkRow.remark = this.currentRemark
        }
        this.remarkDialogVisible = false
        this.currentRemarkRow = null
        this.currentRemark = ''
    },
    openCopyDialogFromTab(fromGroupId) {
        if (!this.canEdit) return
        this.copyFromGroup = fromGroupId
        this.copyToGroups = []
        this.overwriteSteps = true
        this.copyDialogVisible = true
    },
    doCopyScheme() {
        const from = this.copyFromGroup
        const targets = this.copyToGroups || []

        if (!from) return ElMessage.warning('来源分组异常')
        if (targets.length === 0) return ElMessage.warning('请选择至少一个目标分组')
        if (targets.includes(from)) return ElMessage.warning('目标分组不能包含来源分组')

        const fromSteps = this.getStepsForGroup(from)
        if (fromSteps.length === 0) return ElMessage.warning(`来源分组 ${from} 没有步骤可复制`)

        if (this.overwriteSteps) {
            const targetSet = new Set(targets)
            this.postForm.steps = this.postForm.steps.filter(s => !targetSet.has(s.group_id))
        }

        const clonedAll = []
        for (const to of targets) {
            const cloned = fromSteps.map((s) => {
                const { step_id, sort_order, ...rest } = s || {}
                return {
                    ...JSON.parse(JSON.stringify(rest)),
                    step_id: null,
                    group_id: to
                }
            })
            clonedAll.push(...cloned)
        }

        this.postForm.steps.push(...clonedAll)
        targets.forEach((to) => reindexGroupSortOrder(this.postForm.steps, to))
        ElMessage.success(`已将 ${from} 的方案复制到 ${targets.join(', ')}`)
        this.copyDialogVisible = false
    },
    removeStep(row) {
        const groupSteps = this.getStepsForGroup(row.group_id)
        const groupIndex = groupSteps.findIndex(s => s === row)
        const index = this.postForm.steps.indexOf(row)
        if (index > -1) {
            this.postForm.steps.splice(index, 1)
            reindexGroupSortOrder(this.postForm.steps, row.group_id)
            this.recalculateGroupDates(row.group_id, groupIndex > -1 ? groupIndex : 0)
        }
    },
    updateStepAdjuvant(step, antigen) {
        if (!antigen || !antigen.adjuvant_type) return
        if (antigen.adjuvant_type === '弗氏佐剂') {
            step.adjuvant_name = step.stage_name === '一免' ? 'CFA' : 'IFA'
        } else if (antigen.adjuvant_type === 'ADDAVAX') {
            step.adjuvant_name = 'ADDAVAX'
        }
    },
    applyAntigenRouteByType(step, antigen) {
        if (!antigen || step.route === '-') return
        if (antigen.antigen_type === 'LNP') {
            step.route = 'i.m.'
        } else if (antigen.antigen_type === 'DNA') {
            step.route = 'DNA'
        } else {
            return
        }
        this.handleRouteChange(step)
    },
    handleAntigenChange(row, groupId, rowIndex) {
        let antigenIds = Array.isArray(row.antigen_id) ? [...row.antigen_id] : []

        const hasNA = antigenIds.includes('N/A')
        const hasNormalAntigen = antigenIds.some(id => id !== 'N/A')

        if (hasNA && hasNormalAntigen) {
            antigenIds = antigenIds.filter(id => id !== 'N/A')
        }

        row.antigen_id = antigenIds

        if (antigenIds.length === 1 && antigenIds[0] === 'N/A') {
            row.antigen_dose = '-'
            row.adjuvant_name = '-'
            row.cpg_dose = '-'
            row.injection_volume = '-'
            row.route = '-'
            row.injection_site = '-'
        } else {
            if (row.antigen_dose === '-') row.antigen_dose = ''
            if (row.adjuvant_name === '-') row.adjuvant_name = ''
            if (row.cpg_dose === '-') row.cpg_dose = '20µg'
            if (row.injection_volume === '-') row.injection_volume = '100µL'
            if (row.route === '-') row.route = 's.c.'
            if (row.injection_site === '-') row.injection_site = '颈部+尾根部'

            const firstAntigenId = antigenIds.find(id => id !== 'N/A')
            if (firstAntigenId) {
                const antigen = this.postForm.antigens.find(a => String(a.antigen_id) === String(firstAntigenId))
                this.updateStepAdjuvant(row, antigen)
                this.applyAntigenRouteByType(row, antigen)
            }
        }

        this.$nextTick(() => {
            const refName = `antigenSelect_${groupId}_${rowIndex}`
            const selectRef = this.$refs[refName]
            const ins = Array.isArray(selectRef) ? selectRef[0] : selectRef

            if (ins) {
                ins.blur && ins.blur()
            }
        })
    },
    handleStageChange(row) {
        if (row.stage_name === '采血') {
            if (!Array.isArray(row.antigen_id) || row.antigen_id.length === 0 || (row.antigen_id.length === 1 && row.antigen_id[0] !== 'N/A')) {
                row.antigen_id = ['N/A']
                row.antigen_dose = '-'
                row.adjuvant_name = '-'
                row.cpg_dose = '-'
                row.injection_volume = '-'
                row.route = '-'
                row.injection_site = '-'
            }
        } else {
            const antigenIds = Array.isArray(row.antigen_id) ? row.antigen_id : []
            const firstAntigenId = antigenIds.find(id => id !== 'N/A')
            if (firstAntigenId) {
                const antigen = this.postForm.antigens.find(a => String(a.antigen_id) === String(firstAntigenId))
                this.updateStepAdjuvant(row, antigen)
                this.applyAntigenRouteByType(row, antigen)
            }
        }
        if (isMianStage(row.stage_name)) {
            resortMianStepsInGroup(this.postForm.steps, row.group_id)
        }
        const groupSteps = this.getStepsForGroup(row.group_id)
        const startIndex = isMianStage(row.stage_name)
            ? 0
            : groupSteps.findIndex(s => s === row)
        this.recalculateGroupDates(row.group_id, startIndex > -1 ? startIndex : 0)
    },
    handleAntigenAdjuvantTypeChange(antigenRow) {
        if (!antigenRow.antigen_id || !antigenRow.adjuvant_type || antigenRow.adjuvant_type === '无') return

        this.postForm.steps.forEach(step => {
            const ids = Array.isArray(step.antigen_id) ? step.antigen_id.map(String) : []
            if (ids.includes(String(antigenRow.antigen_id))) {
                this.updateStepAdjuvant(step, antigenRow)
            }
        })
    },
    handleAntigenTypeChange(antigenRow) {
        if (!antigenRow.antigen_id) return

        this.postForm.steps.forEach((step) => {
            const ids = Array.isArray(step.antigen_id) ? step.antigen_id.map(String) : []
            if (!ids.includes(String(antigenRow.antigen_id))) return
            const firstAntigenId = ids.find((id) => id !== 'N/A')
            if (firstAntigenId !== String(antigenRow.antigen_id)) return
            this.applyAntigenRouteByType(step, antigenRow)
        })
    },
    handleRouteChange(row) {
        const routeSiteMap = {
            's.c.': '颈部+尾根部',
            'i.p.': '腹腔',
            'i.v.': '尾静脉',
            'i.m.': '大腿肌肉',
            'DNA': '肌肉电转'
        }
        if (routeSiteMap[row.route]) {
            row.injection_site = routeSiteMap[row.route]
        }
    },
    parseDateOnly(value) {
        if (!value) return null
        if (value instanceof Date) {
            if (Number.isNaN(value.getTime())) return null
            return new Date(value.getFullYear(), value.getMonth(), value.getDate())
        }

        const matched = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/)
        if (matched) {
            return new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]))
        }

        const parsed = new Date(value)
        if (Number.isNaN(parsed.getTime())) return null
        return new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate())
    },
    formatDate(date) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    },
    addDays(date, days) {
        const targetDate = new Date(date)
        targetDate.setDate(date.getDate() + days)
        return targetDate
    },
    daysBetween(targetDate, startDate) {
        return Math.round((targetDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    },
    calculateStepDate(row) {
        const startDate = this.parseDateOnly(this.postForm.start_date)
        if (!startDate) return

        const groupSteps = this.getStepsForGroup(row.group_id)
        const currentIndex = groupSteps.findIndex(s => s === row)

        const lastStep = currentIndex > 0 ? groupSteps[currentIndex - 1] : null
        const baseDate = lastStep?.date_actual ? this.parseDateOnly(lastStep.date_actual) : startDate
        if (!baseDate) return

        const interval = lastStep
            ? (row.stage_name === '采血' ? 7 : parseInt(this.postForm.immunization_interval) || 0)
            : 0

        const targetDate = this.addDays(baseDate, interval)

        row.date_actual = this.formatDate(targetDate)
        row.day_relative = this.daysBetween(targetDate, startDate).toString()
    },
    recalculateGroupDates(groupId, startIndex = 0) {
        const groupSteps = this.getStepsForGroup(groupId)
        for (let index = Math.max(0, startIndex); index < groupSteps.length; index += 1) {
            this.calculateStepDate(groupSteps[index])
        }
    },
    recalculateAllStepDates() {
        const groupIds = new Set(this.postForm.steps.map(step => step.group_id).filter(Boolean))
        groupIds.forEach(groupId => this.recalculateGroupDates(groupId))
    },
    handleStepDateChange(row) {
        const startDate = this.parseDateOnly(this.postForm.start_date)
        const targetDate = this.parseDateOnly(row.date_actual)
        if (startDate && targetDate) {
            row.date_actual = this.formatDate(targetDate)
            row.day_relative = this.daysBetween(targetDate, startDate).toString()
        }

        const groupSteps = this.getStepsForGroup(row.group_id)
        const currentIndex = groupSteps.findIndex(s => s === row)
        if (currentIndex > -1) {
            this.recalculateGroupDates(row.group_id, currentIndex + 1)
        }
    },
    async submitForm() {
        if (!this.canEdit) {
            ElMessage.warning('您没有权限保存此草稿')
            return
        }
        if (this.loading) {
            return
        }
        if (!this.postForm.id) {
            ElMessage.error('缺少工作台记录')
            return
        }
        this.loading = true
        try {
          await this.doSubmit({ force: true })
          ElNotification({ type: 'success', message: '草稿已保存' })
        } catch {
          // doSubmit 已统一提示保存错误
        } finally {
          this.loading = false
        }
    },
    async doSubmit({ force = true } = {}) {
        try {
            return await this.queueSchemeSave({ force })
        } catch (err) {
            this.handleSaveFailure(err)
            throw err
        }
    },
    schemeStartBlockReason() {
        const code = String(this.postForm.project_code || '').replace(/\s/g, '')
        if (!code) return '开展前必须填写项目编号'
        if (!String(this.postForm.owner || '').trim()) return '开展前必须选择负责人'
        return ''
    },
    async handleStart() {
        if (!this.canEdit) return
        if (!this.canStart) {
            ElMessage.warning('该状态不能开展')
            return
        }
        if (this.loading) return
        if (!this.postForm.id) {
            ElMessage.error('缺少工作台记录')
            return
        }
        const blocked = this.schemeStartBlockReason()
        if (blocked) {
            ElMessage.warning(blocked)
            return
        }
        if (!canEditSerumProject(this.currentUserInfo, this.postForm)) {
            try {
                await ElMessageBox.confirm(
                  '负责人不是当前用户，开展后你将无法编辑该项目。是否继续？',
                  '确认开展',
                  { type: 'warning' },
                )
            } catch {
                return
            }
        }
        this.loading = true
        try {
            await this.doSubmit({ force: true })
        } catch {
            this.loading = false
            return
        }
        try {
            const saved = await startWorkbench(this.postForm.id)
            ElMessage.success(`已开展，实验号 ${saved.experiment_id}`)
            if (saved?.serum_project_id) {
                if (canOpenSerumEdit(this.currentUserInfo, saved)) {
                    this.$router.replace({ path: '/serum/edit', query: { id: saved.serum_project_id } })
                    return
                }
                if (canAccessSerumDetail(this.currentUserInfo)) {
                    this.$router.replace({ path: '/serum/detail', query: { id: saved.serum_project_id } })
                    return
                }
            }
            this.$router.replace('/serum/workbench')
        } catch (err) {
            notifyApiError(err, { messages: SERUM_ERRORS.workbench.start })
        } finally {
            this.loading = false
        }
    },
    handleCancel() {
        this.$router.push('/serum/workbench')
    },
    cacheGroupId(row) {
        this.groupIdSnapshots.set(row, row.group_id)
    },
    handleGroupIdChange(row, newId) {
        const oldId = this.groupIdSnapshots.get(row) ?? row.group_id

        if (!newId || !String(newId).trim()) {
            ElMessage.error('组别不能为空')
            row.group_id = oldId
            this.$nextTick(() => { row.group_id = oldId })
            return
        }

        if (!oldId || oldId === newId) return

        const duplicate = this.postForm.mouse_groups.some(g => g !== row && g.group_id === newId)
        if (duplicate) {
            ElMessage.error(`组别 ${newId} 已存在，🤡想卡BUG？哼哼~🫵🤣不存在的~`)
            this.$nextTick(() => { row.group_id = oldId })
            return
        }

        this.postForm.steps.forEach(s => {
            if (s.group_id === oldId) s.group_id = newId
        })

        if (this.activeGroupTab === oldId) this.activeGroupTab = newId
        this.groupIdSnapshots.set(row, newId)
    },
    openMouseRegistryDialog(row) {
        this.mouseRegistryEditingRow = row
        this.mouseRegistryDialogVisible = true
    },
    onMouseRegistryConfirm({ mouse_registry, mouse_no_list }) {
        const row = this.mouseRegistryEditingRow
        if (!row) return
        row.mouse_registry = mouse_registry
        row.mouse_no_list = mouse_no_list
    },
    createMouseGroup(groupId, seedWorkbench = false) {
        return {
            group_id: groupId,
            mouse_strain: seedWorkbench ? (this.postForm.mouse_strain || '') : '',
            mouse_strain_category: seedWorkbench ? (this.postForm.mouse_strain_category || '') : '',
            mouse_count: '10',
            age_weeks: '6-8',
            sex: 'F/M',
            cage_position: '',
            vendor: '',
            mouse_no_list: '',
            mouse_registry: null,
            remark: ''
        }
    },
    ensureInitialMouseGroup() {
        if (this.postForm.mouse_groups.length > 0) return
        if (!this.postForm.mouse_strain && !this.postForm.mouse_strain_category) return
        this.postForm.mouse_groups.push(this.createMouseGroup('G1', true))
    },
    addMouseGroup() {
        if (!this.canEdit) return
        const isFirstGroup = this.postForm.mouse_groups.length === 0
        let nextGroupId = 'G1'
        const existingGroups = this.postForm.mouse_groups.map(g => g.group_id)

        // Find the next available group number
        for (let i = 1; i <= 100; i++) {
            const candidateId = `G${i}`
            if (!existingGroups.includes(candidateId)) {
                nextGroupId = candidateId
                break
            }
        }

        this.postForm.mouse_groups.push(this.createMouseGroup(nextGroupId, isFirstGroup))

        // Auto-activate the newly added group
        this.$nextTick(() => {
            this.activeGroupTab = nextGroupId
            this.updateProjectName()
        })
    },
    removeMouseGroup(index) {
        const group = this.postForm.mouse_groups[index]
        if (group && group.group_id) {
            const groupId = group.group_id
            ElMessageBox.confirm(`确定要删除分组 ${groupId} 及其所有步骤吗？`, '确认删除', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                this.postForm.mouse_groups.splice(index, 1)
                this.postForm.steps = this.postForm.steps.filter(s => s.group_id !== groupId)
                if (this.activeGroupTab === groupId) {
                    this.activeGroupTab = this.postForm.mouse_groups.length > 0 ? this.postForm.mouse_groups[0].group_id : null
                }
                this.updateProjectName()
            }).catch(() => {
            })
        } else {
            this.postForm.mouse_groups.splice(index, 1)
            this.updateProjectName()
        }
    },
    addAntigen() {
        if (!this.canEdit) return
        let nextId = 1
        const existingIds = this.postForm.antigens.map(a => parseInt(a.antigen_id)).filter(id => !isNaN(id))
        while (existingIds.includes(nextId)) {
            nextId++
        }

        this.postForm.antigens.push({
            antigen_id: nextId.toString(),
            antigen_name: '',
            antigen_type: '',
            species: '',
            catalog_no: '',
            lot_no: '',
            stock_conc: '',
            vendor: 'BBCTG',
            adjuvant_type: '弗氏佐剂',
            adjuvant_source: '进口'
        })
    },
    handleAntigenPaste(event, row) {
        event.preventDefault()
        const clipboardData = event.clipboardData || window.clipboardData
        const pastedText = clipboardData.getData('text')

        if (!pastedText) return
        const parts = pastedText.split(/\t|\r?\n/)

        if (parts.length === 0) return;
        row.antigen_name = parts[0] || row.antigen_name;
        if (parts.length >= 2) row.catalog_no = parts[1];
        if (parts.length >= 3) row.lot_no = parts[2];
        if (parts.length >= 4) row.stock_conc = parts[3];

        ElMessage.success('已自动填充抗原信息')
    },
    removeAntigen(index) {
        const antigenId = String(this.postForm.antigens[index]?.antigen_id || '').trim()
        let wasReferenced = false
        if (antigenId) {
            this.postForm.steps.forEach((step) => {
                const ids = Array.isArray(step.antigen_id)
                    ? step.antigen_id
                    : String(step.antigen_id || '').split(',')
                const remaining = ids.filter((id) => String(id).trim() !== antigenId)
                if (remaining.length !== ids.length) {
                    step.antigen_id = remaining
                    wasReferenced = true
                }
            })
        }
        this.postForm.antigens.splice(index, 1)
        if (wasReferenced) {
            ElMessage.warning('该抗原已被引用，请记得为相关免疫步骤重新选择抗原')
        }
    },
    addTarget() {
        if (!this.canEdit) return
        this.postForm.titer_targets.push({ name: '', type: '', species: '', batch_no: '', passage: '', cell_count: '', catalog_no: '', source: '' })
    },
    removeTarget(index) {
        this.postForm.titer_targets.splice(index, 1)
    },
    addPC() {
        if (!this.canEdit) return
        this.postForm.titer_pcs.push({ pc_name: '', catalog_batch: '', source: '', concentration: '' })
    },
    removePC(index) {
        this.postForm.titer_pcs.splice(index, 1)
    },
    prepareSubmitData() {
      const payload = {
        id: this.postForm.id,
        scheme_revision: this.postForm.scheme_revision,
      }
      for (const field of [...SCHEME_HEADER_FIELDS, ...SCHEME_CHILD_FIELDS]) {
        payload[field] = this.postForm[field]
      }
      if (payload.owner == null) payload.owner = ''
      if (payload.pm == null) payload.pm = ''
      const submitData = JSON.parse(JSON.stringify(payload))

      if (submitData.steps) {
        const groupIds = [...new Set(submitData.steps.map((s) => s.group_id).filter(Boolean))]
        groupIds.forEach((gid) => reindexGroupSortOrder(submitData.steps, gid))
        submitData.steps.forEach(step => {
          if (Array.isArray(step.antigen_id)) {
            step.antigen_id = step.antigen_id.join(',')
          }
        })
      }

      return submitData
    },
    clearAutoSaveTimer() {
      if (!this.autoSaveTimer) return
      clearTimeout(this.autoSaveTimer)
      this.autoSaveTimer = null
    },
    isRevisionConflict(err) {
      const { backendMessage, httpStatus } = extractApiError(err)
      return httpStatus === 409 || String(backendMessage || '').includes('已被其他用户修改')
    },
    handleSaveFailure(err) {
      if (this.isRevisionConflict(err)) {
        ElMessage.warning('该方案已被其他用户修改，已为你加载最新数据')
        this.initPage(this.$route.query.id)
        return
      }
      notifyApiError(err, { messages: SERUM_ERRORS.workbench.schemeSave })
    },
    triggerAutoSave() {
      if (!this.canEdit) return
      if (!this.activeWorkbenchId || this.loading) return
      this.clearAutoSaveTimer()
      this.autoSaveTimer = setTimeout(() => {
        this.doAutoSave()
      }, 3000)
    },
    captureNewChildRefs() {
      const capture = (key, idField) => (this.postForm[key] || []).filter((item) => !item[idField])
      return {
        mouse_groups: capture('mouse_groups', 'id'),
        antigens: capture('antigens', 'id'),
        steps: capture('steps', 'step_id'),
        titer_targets: capture('titer_targets', 'id'),
        titer_pcs: capture('titer_pcs', 'id'),
      }
    },
    applyChildIds(response, refs) {
      if (!response) return
      const mappings = [
        ['mouse_groups', 'new_mouse_records', 'id'],
        ['antigens', 'new_antigen_records', 'id'],
        ['steps', 'new_step_records', 'step_id'],
        ['titer_targets', 'new_target_records', 'id'],
        ['titer_pcs', 'new_pc_records', 'id'],
      ]
      mappings.forEach(([formKey, responseKey, idField]) => {
        const currentRows = this.postForm[formKey] || []
        const pendingRefs = refs?.[formKey] || []
        const records = response[responseKey] || []
        records.forEach((record, index) => {
          const item = pendingRefs[index]
          if (item && currentRows.includes(item) && !item[idField]) {
            item[idField] = record[idField]
          }
        })
      })
    },
    applySaveResponse(response, submittedProjectCode) {
      if (!response) return
      if (response.id) {
        this.postForm.id = response.id
      }
      const identifiersAreCurrent = this.postForm.project_code === submittedProjectCode
      if (identifiersAreCurrent && response.project_code !== undefined) {
        this.postForm.project_code = response.project_code || ''
      }
      if (identifiersAreCurrent && response.experiment_id) {
        this.postForm.experiment_id = response.experiment_id
      }
      this.postForm.mouse_strain = response.mouse_strain || ''
      this.postForm.mouse_strain_category = response.mouse_strain_category || ''
      if (response.scheme_revision) {
        this.postForm.scheme_revision = response.scheme_revision
      }
    },
    async queueSchemeSave({ force = false } = {}) {
      if (!this.canEdit || !this.activeWorkbenchId) return null
      this.clearAutoSaveTimer()
      if (force || this.formRevision > this.savedRevision) {
        this.saveQueued = true
      }
      if (this.savePromise) return this.savePromise
      if (!this.saveQueued) return null

      const workbenchId = this.activeWorkbenchId
      this.savePromise = (async () => {
        let lastResponse = null
        while (this.saveQueued && this.activeWorkbenchId === workbenchId) {
          this.saveQueued = false
          const revision = this.formRevision
          const refs = this.captureNewChildRefs()
          const submitData = this.prepareSubmitData()
          const response = await saveWorkbenchScheme(submitData)
          if (this.activeWorkbenchId !== workbenchId) break

          this.applyingServerState = true
          try {
            this.applySaveResponse(response, submitData.project_code)
            this.applyChildIds(response, refs)
            this.savedRevision = Math.max(this.savedRevision, revision)
          } finally {
            await this.$nextTick()
            this.applyingServerState = false
          }
          lastResponse = response
          if (this.formRevision > this.savedRevision) this.saveQueued = true
        }
        return lastResponse
      })()

      this.autoSaving = true
      try {
        return await this.savePromise
      } finally {
        this.savePromise = null
        this.autoSaving = false
      }
    },
    async flushPendingSave() {
      this.clearAutoSaveTimer()
      if (!this.canEdit || !this.activeWorkbenchId) return
      if (this.savePromise) {
        await this.savePromise
      }
      if (this.formRevision > this.savedRevision) {
        await this.doSubmit({ force: false })
      }
    },
    async doAutoSave() {
      if (!this.canEdit) return
      if (this.loading || !this.activeWorkbenchId) return
      try {
        await this.doSubmit({ force: false })
      } catch (err) {
        // doSubmit 已统一提示保存错误
      }
    },
    updateProjectName() {
        const targetName = this.postForm.target_name || ''
        const mouseStrains = this.postForm.mouse_groups
            .map(g => g.mouse_strain)
            .filter(s => s && s.trim() !== '')
            .filter((value, index, self) => self.indexOf(value) === index)

        this.postForm.project_name = `${targetName}基于${mouseStrains.join(',')}的抗体发现`
    }
  }
}
</script>

<style scoped>
.workbench-scheme-page {
  padding: 10px 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}
.box-card {
  --el-card-border-color: var(--el-border-color-lighter);
  --el-card-border-radius: 8px;

  margin-bottom: 20px;
}
.scheme-detail-editor.is-readonly {
  pointer-events: none;
}
.scheme-detail-editor.is-readonly :deep(.el-input__wrapper),
.scheme-detail-editor.is-readonly :deep(.el-select__wrapper) {
  background-color: var(--el-disabled-bg-color);
  box-shadow: 0 0 0 1px var(--el-disabled-border-color) inset;
}
.scheme-detail-editor.is-readonly :deep(input),
.scheme-detail-editor.is-readonly :deep(textarea) {
  color: var(--el-disabled-text-color);
}
.workbench-scheme-page :deep(.el-button--small) {
  height: 28px;
  padding: 7px 15px;
  font-size: 12px;
  border-radius: 4px;
}
.workbench-scheme-page :deep(.el-input--small) {
  --el-input-height: 28px;

  font-size: 12px;
}
.workbench-scheme-page :deep(.el-input--small .el-input__wrapper),
.workbench-scheme-page :deep(.el-select--small .el-select__wrapper) {
  min-height: 28px;
  font-size: 12px;
}
.workbench-scheme-page :deep(.el-table--small) {
  font-size: 12px;
}
.workbench-scheme-page :deep(.el-table--small .el-table__cell) {
  padding: 6px 0;
}
.header-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
  font-weight: normal;
}
.readonly-hint {
  margin-right: 10px;
  color: #909399;
  font-size: 12px;
}
.basic-info-card :deep(.el-form-item__label) {
  font-weight: 700;
}
.target-selected-text {
    flex: 0 1 auto;
    min-width: 0;
    max-width: calc(100% - 24px);
    overflow: hidden;
    color: var(--el-text-color-regular);
    font: inherit;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.target-name-select :deep(.el-select__selection) {
    flex-wrap: nowrap;
    overflow: hidden;
}
.target-name-select :deep(.el-select__input-wrapper) {
    flex: 1 1 24px;
    min-width: 24px;
}
:deep(.el-select__selection.is-near) .target-selected-text {
    margin-left: 7px;
}
.target-option {
    display: flex;
    align-items: center;
    gap: 16px;
    width: 100%;
}
.target-option__name {
    flex-shrink: 0;
    min-width: 130px;
}
.target-option__alias {
    overflow: hidden;
    color: var(--el-text-color-secondary);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.target-option--editing :deep(.el-input) {
    flex: 1;
    min-width: 140px;
}
.small-header {
    font-size: 15px;
    line-height: 28px;
}
.sub-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    font-size: 13px;
    font-weight: bold;
    color: #606266;
}
.delete-btn {
    cursor: pointer;
    color: #f56c6c;
    font-size: 16px;
    vertical-align: middle;
}
.delete-btn:hover {
    color: #dd3d3d;
}

/* Keep border on active tab for better visual consistency */
.el-tabs--card :deep(.el-tabs__item.is-active) {
    border-bottom-color: #e4e7ed !important;
}

/* Set tab width */
.el-tabs--card :deep(.el-tabs__item) {
    min-width: 91px;
    text-align: center;
}

/* Remark icon styling */
.remark-icon {
    color: #909399;
    vertical-align: middle;
}

.remark-icon.has-remark {
    color: #409EFF;
}

.remark-icon:hover {
    color: #66b1ff;
}

/* Copy dialog styling */
.copy-dialog-title {
    font-size: 18px;
    font-weight: bold;
    display: block;
    text-align: center;
}

.copy-dialog :deep(.el-dialog) {
    border-radius: 12px;
}

.copy-dialog :deep(.el-dialog__header) {
    border-radius: 12px 12px 0 0;
}

.copy-dialog :deep(.el-dialog__body) {
    border-radius: 0 0 12px 12px;
    padding: 20px 30px;
}

.copy-dialog :deep(.el-form-item__label) {
    text-align: left;
}

.copy-dialog :deep(.el-form-item) {
    margin-bottom: 18px;
}

.copy-dialog :deep(.el-form-item__content) {
    text-align: left;
}

/* Hide multi-select tags to show as single-select */
.antigen-select-hidden :deep(.el-select__tags) {
    display: none;
}

.antigen-select-hidden {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 28px;
}

.antigen-select-hidden :deep(.el-select__wrapper) {
    height: 28px;
    max-height: 28px;
    min-height: 28px;
    overflow: hidden;
    opacity: 0;
}

.antigen-select-hidden :deep(.el-select__selection),
.antigen-select-hidden :deep(.el-select__selected-item),
.antigen-select-hidden :deep(.el-select__input-wrapper),
.antigen-select-hidden :deep(.el-select__placeholder) {
    max-height: 28px;
    overflow: hidden;
    opacity: 0;
}

/* Antigen select wrapper styling */
.antigen-select-wrapper {
    position: relative;
    width: 100%;
    height: 28px;
    overflow: hidden;
}

.mouse-no-list-input :deep(.el-input__wrapper) {
    cursor: pointer;
}

.mouse-no-list-input :deep(.el-input__inner) {
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.antigen-display-text {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1;
    box-sizing: border-box;
    width: 100%;
    height: 28px;
    line-height: 28px;
    padding: 0 30px 0 15px;
    font-size: 12px;
    background: #fff;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #303133;
    pointer-events: none;
}

.antigen-display-text.is-placeholder {
    color: #C0C4CC;
}

.antigen-select-hidden :deep(.el-input__inner) {
    opacity: 0;
}
</style>
