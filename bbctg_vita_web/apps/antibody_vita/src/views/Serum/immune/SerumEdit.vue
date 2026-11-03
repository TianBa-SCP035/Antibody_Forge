<template>
  <div
    class="createPost-main-container"
    :class="{ 'is-readonly': !canEdit }"
    v-loading="loading"
  >
    <el-card class="box-card basic-info-card" :body-style="{ padding: '18px' }">
      <template #header>
        <div class="clearfix">
          <span>1. 项目基础信息 (Project Info)</span>
          <div style="float: right;">
              <span v-if="!canEdit" class="readonly-hint">只读</span>
              <span v-if="autoSaving" style="margin-right: 10px; color: var(--el-color-primary); font-size: 12px;">
                  <el-icon class="is-loading"><Loading /></el-icon> 自动保存中...
              </span>
              <el-button size="small" type="primary" title="停 3 秒自动保存、右键保存并新建" @click="submitForm" @contextmenu.prevent="submitForm($event, true)" :loading="loading" :disabled="loading || autoSaving || !canEdit">保存</el-button>
              <el-button size="small" @click="handleCancel">取消</el-button>
          </div>
        </div>
      </template>
      
      <el-form ref="postForm" :model="postForm" :rules="rules" label-width="100px">
        <!-- Row 1: 项目编号, 实验ID, 负责人 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="项目编号" prop="project_code">
              <el-input v-model="postForm.project_code" placeholder="输入后自动生成实验ID" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="实验ID" prop="experiment_id">
              <el-input v-model="postForm.experiment_id" disabled placeholder="根据项目编号自动生成" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="负责人" prop="owner">
              <UserSelect
                v-model="postForm.owner"
                :options="ownerOptions"
                placeholder="选择负责人"
                :disabled="!canEdit || !canAssignProjectOwner"
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
                title="左键单选，右键多选；Shift+Enter 可直接录入未入库靶点名称"
                style="width: 100%"
                :disabled="!canEdit"
                @change="handleTargetChange"
                @focus="handleTargetFocus"
                @visible-change="onTargetDropdownVisible"
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
                    title="左键单选，右键多选，Shift+右键自定义项目中的显示名称"
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
            <el-form-item label="靶点类型" prop="target_type">
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
            <el-form-item label="靶点大小" prop="target_size">
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
            <el-form-item label="项目名称" prop="project_name">
              <el-input v-model="postForm.project_name" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="课题类型" prop="study_type">
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
            <el-form-item label="产品经理" prop="pm">
              <UserSelect
                v-model="postForm.pm"
                :options="pmOptions"
                placeholder="选择产品经理"
                :disabled="!canEdit"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- Row 4: 开始日期, 检测方法, 项目状态 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker v-model="postForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" :disabled="!canEdit" @change="recalculateAllStepDates" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检测方法" prop="assay_method">
              <AssayMethodEditor
                v-model:assay-method="postForm.assay_method"
                v-model:facs-plate-count="postForm.facs_plate_count"
                v-model:elisa-plate-count="postForm.elisa_plate_count"
                :disabled="!canEdit"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目状态" prop="project_status">
              <el-select v-model="postForm.project_status" style="width:100%" filterable allow-create default-first-option :disabled="!canEdit">
                <el-option v-for="item in projectStatusOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- Row 5: 免疫间隔, 备注 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="免疫间隔" prop="immunization_interval">
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
            <el-form-item label="项目目的" prop="project_purpose">
              <el-input v-model="postForm.project_purpose" type="textarea" :rows="2" placeholder="请输入项目目的" :disabled="!canEdit" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 2. Antigens (Full Width) -->
    <el-card class="box-card" :body-style="{ padding: '15px' }">
        <template #header>
          <div class="clearfix small-header">
            <span>2. 抗原信息 (Antigens)</span>
                <el-button v-if="canEdit" style="float: right; padding: 3px 0" link @click="addAntigen">添加抗原</el-button>
          </div>
        </template>
        <el-table :data="postForm.antigens" border size="small" style="width: 100%" :inert="!canEdit">
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
                        <el-option label="猫" value="猫" />
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
        <el-table :data="postForm.mouse_groups" border size="small" style="width: 100%" :inert="!canEdit">
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
                    <el-select v-model="row.mouse_strain" size="small" filterable allow-create default-first-option style="width:100%" placeholder="选择小鼠品系" @change="updateProjectName">
                        <el-option
                          v-for="item in mouseStrainOptions"
                          :key="item"
                          :label="item"
                          :value="item"
                        />
                    </el-select>
                </template>
            </el-table-column>
            <el-table-column label="归类鼠型" min-width="120">
                    <template #default="{ row }">
                    <el-select v-model="row.mouse_strain_category" size="small" filterable allow-create default-first-option style="width:100%" placeholder="选择归类鼠型">
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

    <!-- 4. Immunization Scheme (Moved to Top) -->
    <el-card class="box-card" :body-style="{ padding: '15px' }">
      <template #header>
        <div class="clearfix small-header">
          <span>4. 免疫方案 (Immunization Scheme)</span>
          <div v-if="canEdit" class="scheme-header-actions">
            <el-checkbox
              v-model="autoRecalcDates"
              size="small"
              class="auto-date-checkbox"
              title="开启时修改日期或阶段会顺延后续步骤；关闭后只改当前步。打开开关本身不会重算已有日期"
            >
              自动顺延日期
            </el-checkbox>
            <el-button
              v-if="postForm.mouse_groups.length > 0"
              style="padding: 3px 0"
              link
              @click="addStepToGroup(activeGroupTab)"
            >
              添加步骤
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-if="postForm.mouse_groups.length === 0" style="text-align: center; color: var(--el-text-color-secondary); padding: 20px;">
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
              
              <el-table :data="getStepsForGroup(group.group_id)" border size="small" style="width:100%" :inert="!canEdit">
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
                     <template #default="{ row }">
                        <ListFilterSelect
                            :model-value="row.antigen_id"
                            joined
                            clearable
                            size="small"
                            placeholder="选择抗原"
                            title="左键单选，右键多选"
                            @change="handleAntigenChange(row, $event)"
                        >
                            <template #tag>{{ getAntigenDisplay(row.antigen_id) }}</template>
                            <el-option v-for="a in postForm.antigens" :key="a.antigen_id" :label="a.antigen_name || a.antigen_id" :value="a.antigen_id" />
                            <el-option label="N/A(不适用)" value="N/A" />
                        </ListFilterSelect>
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
            <el-input :value="copyFromGroup" disabled style="background-color: var(--el-fill-color-light);" />
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



    <!-- 5. Titer Section (Ref) -->
    <div ref="titerCard">
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
                 <el-table :data="postForm.titer_targets" border size="small" :inert="!canEdit">
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
                 <el-table :data="postForm.titer_pcs" border size="small" :inert="!canEdit">
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
    </div>

    <!-- 6. Danger Zone: Delete Experiment -->
    <el-card v-if="postForm.id" class="box-card danger-zone-card" :body-style="{ padding: '20px' }">
      <template #header>
        <div class="clearfix danger-zone-header">
          <el-icon style="margin-right: 8px;"><WarningFilled /></el-icon>
          <span>6. 危险区域 (Danger Zone)</span>
        </div>
      </template>
      
      <div class="danger-zone-content">
        <div class="danger-zone-text">
          <h4 style="margin: 0 0 8px 0; color: var(--el-color-danger);">
            <el-icon><Delete /></el-icon> 删除此实验项目
          </h4>
          <p style="margin: 0; color: var(--el-text-color-regular); font-size: 13px;">
            删除后将无法恢复，所有相关数据（小鼠分组、抗原信息、免疫步骤、效价检测等）都将被永久清除。请谨慎操作。
          </p>
        </div>
        <el-button type="danger" size="small" :disabled="!canDeleteForm()" @click="handleDelete" plain>
          <el-icon><Delete /></el-icon> 删除实验项目
        </el-button>
      </div>
    </el-card>

    <MouseRegistryDialog
      v-model="mouseRegistryDialogVisible"
      :group="mouseRegistryEditingRow"
      @confirm="onMouseRegistryConfirm"
    />

  </div>
</template>

<script>
import { useUserStore } from '@vben/stores'

import {
  Delete,
  Edit,
  Loading,
  Plus,
  WarningFilled,
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

import { notifyApiError } from '#/api/errors'
import {
  deleteSerum,
  fetchDetail,
  getSerumFilterOptions,
  saveSerum,
} from '#/api/serum'
import { SERUM_ERRORS } from '../shared/errors'
import serumSchemeMixin, { reindexGroupSortOrder } from '../shared/serumSchemeMixin'
import ListFilterSelect from '#/components/ListFilterSelect.vue'
import MouseRegistryDialog from '../shared/MouseRegistryDialog.vue'
import AssayMethodEditor from '../shared/AssayMethodEditor.vue'
import UserSelect from '#/components/UserSelect.vue'
import {
  canEditAllSerumProjects,
  canCreateSerumProject,
  canDeleteSerumProject,
  canEditSerumProject,
  getSerumUserName,
} from '#/utils/serumPermission'
import {
  SERUM_PROJECT_STATUS_DEFAULT,
  SERUM_PROJECT_STATUS_OPTIONS,
} from '#/utils/serumProjectStatus'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'

function createEmptyPostForm() {
  return {
    id: undefined,
    project_revision: '',
    experiment_id: '',
    project_code: '',
    project_name: '',
    project_purpose: '',
    owner: '',
    start_date: '',
    project_status: SERUM_PROJECT_STATUS_DEFAULT,
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
    mouse_groups: [],
    steps: [],
    antigens: [],
    titer_targets: [],
    titer_pcs: [],
  }
}

export default {
  mixins: [serumSchemeMixin],
  name: 'SerumEdit',
  components: {
    ListFilterSelect,
    MouseRegistryDialog,
    AssayMethodEditor,
    UserSelect,
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
    WarningFilled,
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
      postForm: createEmptyPostForm(),
      loadFailed: false,
      ownerOptions: [],
      pmOptions: [],
      projectStatusOptions: SERUM_PROJECT_STATUS_OPTIONS,
      rules: {
        project_code: [{ required: true, message: '必填', trigger: 'blur' }],
        owner: [{ required: true, message: '必填', trigger: 'blur' }],
      },
      loadedRouteIdentity: '',
      routeTransitionPending: false,
      tabDataFetchedAt: 0,
    }
  },
  computed: {
    currentUserInfo() {
      return this.userStore.userInfo || {}
    },
    currentUserName() {
      return getSerumUserName(this.currentUserInfo)
    },
    canAssignProjectOwner() {
      return canEditAllSerumProjects(this.currentUserInfo)
    },
    canEdit() {
      return this.canSaveForm()
    },
  },
  created() {
    const id = this.$route.query.id
    this.initPage(id)
  },
  activated() {
    if (this.$route.name !== 'SerumEdit') return
    if (this.initializing) return
    if (this.loadedRouteIdentity !== this.editRouteIdentity(this.$route)) {
      this.initPage(this.$route.query.id)
      return
    }
    if (shouldRefreshTabData(this.tabDataFetchedAt)) {
      const id = this.$route.query.id
      if (id) {
        this.initPage(id)
      }
    }
  },
  beforeRouteUpdate(to, from, next) {
    if (this.editRouteIdentity(to) === this.loadedRouteIdentity) {
      next()
      return
    }
    const continueNavigation = () => {
      this.routeTransitionPending = false
      this.initializing = true
      next()
      this.$nextTick(() => this.initPage(to.query.id))
    }
    this.routeTransitionPending = true
    this.flushPendingSave()
      .then(continueNavigation)
      .catch((err) => {
        this.routeTransitionPending = false
        this.handleSaveFailure(err)
        next(false)
      })
  },
  beforeRouteLeave(to, from, next) {
    this.routeTransitionPending = true
    this.flushPendingSave()
      .then(() => {
        this.routeTransitionPending = false
        next()
      })
      .catch((err) => {
        this.routeTransitionPending = false
        this.handleSaveFailure(err)
        next(false)
      })
  },
  methods: {
    async initPage(id) {
      const isLatest = this.initRequest.begin()
      this.targetRequest.cancel()
      this.targetLoading = false
      const routeIdentity = id ? `id:${id}` : 'new'
      let loadSucceeded = false
      this.clearAutoSaveTimer()
      this.loading = Boolean(id)
      this.loadFailed = false
      this.initializing = true
      if (routeIdentity !== this.loadedRouteIdentity) {
        this.resetTransientEditors()
        this.postForm = createEmptyPostForm()
        this.targetDisplayNames = {}
        this.targetOptions = []
        this.activeGroupTab = null
      }
      try {
        const tasks = [
          getSerumFilterOptions().catch((error) => {
            notifyApiError(error, { messages: { default: '加载负责人与 PM 选项失败，下拉暂时为空' } })
            return null
          }),
        ]
        if (id) {
          tasks.push(fetchDetail(id))
        }
        const results = await Promise.all(tasks)
        if (!isLatest()) return
        const filterOptions = results[0]
        this.ownerOptions = filterOptions?.owners || []
        this.pmOptions = filterOptions?.pms || []
        if (id) {
          const detail = results[1]
          const targetCodes = Array.isArray(detail.target_codes) ? detail.target_codes : []
          this.resetTransientEditors()
          this.postForm = {
            ...createEmptyPostForm(),
            ...detail,
            target_codes: targetCodes,
            mouse_groups: detail.mouse_groups || [],
            antigens: detail.antigens || [],
            steps: detail.steps || [],
            titer_targets: detail.titer_targets || [],
            titer_pcs: detail.titer_pcs || [],
          }
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
              if (!Array.isArray(step.antigen_id)) {
                step.antigen_id = String(step.antigen_id || '')
                  .split(',')
                  .map((item) => item.trim())
                  .filter(Boolean)
              }
            })
          }
          if (this.postForm.mouse_groups.length > 0) {
            this.activeGroupTab = this.postForm.mouse_groups[0].group_id
          }
          this.autoRecalcDates = this.shouldAutoRecalcDates()
        } else {
          const currentUser = this.currentUserName
          this.postForm.owner = currentUser.split(' ')[0]
          this.autoRecalcDates = true
        }
        loadSucceeded = true
      } catch (err) {
        if (!isLatest()) return
        this.loadFailed = true
        notifyApiError(err, { messages: SERUM_ERRORS.edit.loadPage })
      } finally {
        if (!isLatest()) return
        this.loading = false
        if (!loadSucceeded) {
          this.$nextTick(() => {
            this.initializing = false
          })
          return
        }
        this.tabDataFetchedAt = Date.now()
        this.loadedRouteIdentity = routeIdentity
        this.formRevision = 0
        this.savedRevision = 0
        this.saveQueued = false
        this.$nextTick(() => {
          this.initializing = false
        })
      }
    },
    submitForm(event, isRightClick = false) {
        if (!this.canSaveForm()) {
            ElMessage.warning('您没有权限保存此项目')
            return
        }
        if (this.loading || this.initializing) return
        this.loading = true
        this.doSubmit(isRightClick)
    },
    doSubmit(isRightClick) {
        this.$refs.postForm.validate(async (valid) => {
            if (!valid) {
                this.loading = false
                return
            }
            try {
                await this.queueFormSave({ force: true })
                ElNotification({ type: 'success', message: '保存成功' })
                if (isRightClick) {
                    await this.initPage()
                    this.$router.replace({ name: 'SerumEdit', query: {} })
                }
            } catch (err) {
                this.handleSaveFailure(err, SERUM_ERRORS.edit.save)
            } finally {
                this.loading = false
            }
        })
    },
    handleCancel() {
        this.$router.go(-1)
    },
    handleDelete() {
        if (!this.canDeleteForm()) {
            ElMessage.warning('您没有权限删除此项目')
            return
        }
        ElMessageBox.confirm('确定移除这个实验吗？工作台来源项目将撤回为草稿，其他项目将永久删除；已有下游效价数据时不能操作。', '警告', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
        }).then(() => {
            this.loading = true
            deleteSerum(this.postForm.id).then((result) => {
                const message = result?.action === 'reverted' ? '已撤回为工作台草稿' : '删除成功'
                ElNotification({ type: 'success', message })
                this.loading = false
                this.$router.push('/serum/list')
            }).catch((err) => {
                this.loading = false
                notifyApiError(err, { messages: SERUM_ERRORS.edit.delete })
            })
        }).catch(() => {
            // User cancelled
        })
    },
    addMouseGroup() {
        if (!this.canEdit) return
        // Smart auto-increment for group_id
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
        
        this.postForm.mouse_groups.push({
            group_id: nextGroupId,
            mouse_strain: '',
            mouse_strain_category: '',
            mouse_count: '10',
            age_weeks: '6-8',
            sex: 'F/M',
            cage_position: '',
            vendor: '',
            mouse_no_list: '',
            mouse_registry: null,
            remark: ''
        })
        
        // Auto-activate the newly added group
        this.$nextTick(() => {
            this.activeGroupTab = nextGroupId
            this.updateProjectName()
        })
    },
    editRouteIdentity(route) {
      const id = route?.query?.id
      return id ? `id:${id}` : 'new'
    },
    async syncEditRouteId() {
      if (!this.postForm.id) return
      const nextId = String(this.postForm.id)
      const routeId = String(this.$route.query.id ?? '')
      if (routeId === nextId) return
      this.loadedRouteIdentity = `id:${nextId}`
      if (this.routeTransitionPending) return
      try {
        await this.$router.replace({
          name: 'SerumEdit',
          query: { ...this.$route.query, id: nextId },
        })
      } catch (err) {
        this.loadedRouteIdentity = this.editRouteIdentity(this.$route)
        ElMessage.warning('项目已保存，但页面地址更新失败，请重新打开该项目')
      }
    },
    prepareSubmitData() {
      const submitData = JSON.parse(JSON.stringify(this.postForm))

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
    handleSaveFailure(err, messages = SERUM_ERRORS.edit.autoSave) {
      if (this.isRevisionConflict(err)) {
        ElMessage.warning('该项目已被其他用户修改，已为你加载最新数据')
        this.initPage(this.$route.query.id)
        return
      }
      notifyApiError(err, { messages })
    },
    triggerAutoSave() {
      if (!this.canSaveForm()) return
      if (!this.postForm.project_code || !this.postForm.owner || this.loading) return
      this.clearAutoSaveTimer()
      this.autoSaveTimer = setTimeout(() => {
        this.doAutoSave()
      }, 3000)
    },
    applySaveResponse(response, submittedProjectCode) {
      if (!response) return
      if (response.id) {
        this.postForm.id = response.id
      }
      const identifiersAreCurrent = this.postForm.project_code === submittedProjectCode
      if (identifiersAreCurrent && response.project_code) {
        this.postForm.project_code = response.project_code
      }
      if (identifiersAreCurrent && response.experiment_id) {
        this.postForm.experiment_id = response.experiment_id
      }
      if (response.project_revision) {
        this.postForm.project_revision = response.project_revision
      }
    },
    async saveFormSnapshot() {
      const refs = this.captureNewChildRefs()
      const submitData = this.prepareSubmitData()
      const response = await saveSerum(submitData)
      this.applyingServerState = true
      try {
        this.applySaveResponse(response, submitData.project_code)
        this.applyChildIds(response, refs)
      } finally {
        await this.$nextTick()
        this.applyingServerState = false
      }
      if (response?.id) {
        await this.syncEditRouteId()
      }
      return response
    },
    async queueFormSave({ force = false } = {}) {
      if (!this.canSaveForm()) return null
      this.clearAutoSaveTimer()
      if (force || this.formRevision > this.savedRevision) {
        this.saveQueued = true
      }
      if (this.savePromise) {
        const result = await this.savePromise
        if (this.formRevision <= this.savedRevision) return result
        return this.queueFormSave({ force })
      }
      if (!this.saveQueued) return null

      this.savePromise = (async () => {
        let lastResponse = null
        while (this.saveQueued) {
          this.saveQueued = false
          const revision = this.formRevision
          lastResponse = await this.saveFormSnapshot()
          this.savedRevision = Math.max(this.savedRevision, revision)
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
      if (!this.canSaveForm() || !this.postForm.project_code || !this.postForm.owner) return
      if (this.savePromise) {
        await this.savePromise
      }
      if (this.formRevision > this.savedRevision) {
        await this.queueFormSave()
      }
    },
    async doAutoSave() {
      if (!this.canSaveForm()) return
      if (this.loading || !this.postForm.project_code || !this.postForm.owner) return
      try {
        await this.queueFormSave()
      } catch (err) {
        this.handleSaveFailure(err)
      }
    },
    canSaveForm() {
      if (this.loadFailed) return false
      if (this.postForm.id) {
        return canEditSerumProject(this.currentUserInfo, this.postForm)
      }
      return canCreateSerumProject(this.currentUserInfo)
    },
    canDeleteForm() {
      return !this.loadFailed && Boolean(this.postForm.id) && canDeleteSerumProject(this.currentUserInfo)
    }
  }
}
</script>

<style scoped>
.createPost-main-container {
  padding: 10px 20px;
  background-color: var(--el-fill-color-light);
  min-height: 100vh;
}
.box-card {
  --el-card-border-color: var(--el-border-color-lighter);
  --el-card-border-radius: 8px;

  margin-bottom: 20px;
}
.createPost-main-container.is-readonly {
  --el-disabled-bg-color: var(--el-fill-color-blank);
  --el-disabled-border-color: var(--el-border-color);
  --el-disabled-text-color: var(--el-text-color-regular);
}
.createPost-main-container.is-readonly :deep(.el-select__wrapper.is-disabled) {
  background-color: var(--el-fill-color-blank);
  color: var(--el-text-color-regular);
  cursor: default;
}
.readonly-hint {
  margin-right: 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.createPost-main-container :deep(.el-button--small) {
  height: 28px;
  padding: 7px 15px;
  font-size: 12px;
  border-radius: 4px;
}
.createPost-main-container :deep(.el-input--small) {
  --el-input-height: 28px;

  font-size: 12px;
}
.createPost-main-container :deep(.el-input--small .el-input__wrapper),
.createPost-main-container :deep(.el-select--small .el-select__wrapper) {
  min-height: 28px;
  font-size: 12px;
}
.createPost-main-container :deep(.el-table--small) {
  font-size: 12px;
}
.createPost-main-container :deep(.el-table--small .el-table__cell) {
  padding: 6px 0;
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
.scheme-header-actions {
    float: right;
    display: inline-flex;
    align-items: center;
    gap: 14px;
}
.auto-date-checkbox {
    height: 28px;
    margin-right: 0;
    font-weight: normal;
}
.sub-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    font-size: 13px;
    font-weight: bold;
    color: var(--el-text-color-regular);
}
.delete-btn {
    cursor: pointer;
    color: var(--el-color-danger);
    font-size: 16px;
    vertical-align: middle;
}
.delete-btn:hover {
    color: #dd3d3d;
}

/* Keep border on active tab for better visual consistency */
.el-tabs--card :deep(.el-tabs__item.is-active) {
    border-bottom-color: var(--el-border-color-light) !important;
}

/* Set tab width */
.el-tabs--card :deep(.el-tabs__item) {
    min-width: 91px;
    text-align: center;
}

/* Remark icon styling */
.remark-icon {
    color: var(--el-text-color-secondary);
    vertical-align: middle;
}

.remark-icon.has-remark {
    color: var(--el-color-primary);
}

.remark-icon:hover {
    color: #66b1ff;
}

/* Danger Zone Styling */
.danger-zone-card {
    border: 2px solid var(--el-color-danger);
    background-color: var(--el-color-danger-light-9);
}

.danger-zone-header {
    color: var(--el-color-danger);
    font-weight: bold;
}

.danger-zone-header :deep(.el-icon) {
    vertical-align: -2px;
}

.danger-zone-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.danger-zone-text {
    flex: 1;
}

.danger-zone-text h4 {
    font-weight: bold;
}

.danger-zone-text h4 :deep(.el-icon),
.danger-zone-content :deep(.el-button .el-icon) {
    margin-right: 4px;
    vertical-align: -2px;
}

@media (max-width: 768px) {
    .danger-zone-content {
        flex-direction: column;
        align-items: flex-start;
    }
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

.mouse-no-list-input :deep(.el-input__wrapper) {
    cursor: pointer;
}

.mouse-no-list-input :deep(.el-input__inner) {
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
