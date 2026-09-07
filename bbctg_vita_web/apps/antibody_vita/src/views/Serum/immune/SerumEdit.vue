<template>
  <div class="createPost-main-container" v-loading="loading">
    <el-card class="box-card basic-info-card" :body-style="{ padding: '18px' }">
      <template #header>
        <div class="clearfix">
          <span>1. 项目基础信息 (Project Info)</span>
          <div style="float: right;">
              <span v-if="autoSaving" style="margin-right: 10px; color: #409EFF; font-size: 12px;">
                  <el-icon class="is-loading"><Loading /></el-icon> 自动保存中...
              </span>
              <el-button size="small" type="primary" @click="submitForm" @contextmenu.prevent="submitForm($event, true)" :loading="loading" :disabled="loading || autoSaving || !canSaveForm()">保存</el-button>
              <el-button size="small" @click="handleCancel">取消</el-button>
          </div>
        </div>
      </template>
      
      <el-form ref="postForm" :model="postForm" :rules="rules" label-width="100px">
        <!-- Row 1: 项目编号, 实验ID, 负责人 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="项目编号" prop="project_code">
              <el-input v-model="postForm.project_code" placeholder="输入后自动生成实验ID" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="实验ID" prop="experiment_id">
              <el-input v-model="postForm.experiment_id" disabled placeholder="根据项目编号自动生成" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="负责人" prop="owner">
              <SerumUserSelect
                v-model="postForm.owner"
                :options="ownerOptions"
                placeholder="选择负责人"
                :disabled="!canAssignProjectOwner"
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
            <el-form-item label="靶点类型" prop="target_type">
              <el-select v-model="postForm.target_type" style="width:100%" filterable allow-create default-first-option placeholder="选择或输入靶点类型">
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
              <el-select v-model="postForm.target_size" style="width:100%" filterable allow-create default-first-option placeholder="选择或输入靶点大小">
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
              <el-input v-model="postForm.project_name" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="课题类型" prop="study_type">
              <el-select v-model="postForm.study_type" style="width:100%" filterable allow-create default-first-option placeholder="选择或输入课题类型">
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
              <SerumUserSelect
                v-model="postForm.pm"
                :options="pmOptions"
                placeholder="选择产品经理"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- Row 4: 开始日期, 检测方法, 项目状态 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker v-model="postForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" @change="recalculateAllStepDates" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检测方法" prop="assay_method">
              <AssayMethodEditor
                v-model:assay-method="postForm.assay_method"
                v-model:facs-plate-count="postForm.facs_plate_count"
                v-model:elisa-plate-count="postForm.elisa_plate_count"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目状态" prop="project_status">
              <el-select v-model="postForm.project_status" style="width:100%" filterable allow-create default-first-option>
                <el-option v-for="item in projectStatusOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- Row 5: 免疫间隔, 备注 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="免疫间隔" prop="immunization_interval">
              <el-input v-model="postForm.immunization_interval" placeholder="天数" @change="recalculateAllStepDates">
                <template #append>天</template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="实验备注">
              <el-input v-model="postForm.remark" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- Row 6: 项目目的 -->
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="项目目的" prop="project_purpose">
              <el-input v-model="postForm.project_purpose" type="textarea" :rows="2" placeholder="请输入项目目的" />
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
                <el-button style="float: right; padding: 3px 0" link @click="addAntigen">添加抗原</el-button>
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
                <el-table-column label="操作" width="50" align="center">
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
            <el-button style="float: right; padding: 3px 0" link @click="addMouseGroup">添加分组</el-button>
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
                <el-table-column label="操作" width="50" align="center">
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
          <el-button v-if="postForm.mouse_groups.length > 0" style="float: right; padding: 3px 0" link @click="addStepToGroup(activeGroupTab)">添加步骤</el-button>
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
                <el-table-column label="操作" min-width="50" align="center">
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
                    <el-button link @click="addTarget">
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
                    <el-table-column width="50" align="center">
                        <template #default="{ $index }">
                            <el-icon class="delete-btn" @click="removeTarget($index)"><Delete /></el-icon>
                        </template>
                    </el-table-column>
                </el-table>
            </el-col>
            
            <el-col :span="24">
                 <div class="sub-header">
                    <span>阳性对照</span>
                    <el-button link @click="addPC">
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
                     <el-table-column width="50" align="center">
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
          <h4 style="margin: 0 0 8px 0; color: #F56C6C;">
            <el-icon><Delete /></el-icon> 删除此实验项目
          </h4>
          <p style="margin: 0; color: #606266; font-size: 13px;">
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

import { extractApiError, notifyApiError } from '#/api/errors'
import {
  deleteSerum,
  fetchDetail,
  fetchSerumTargetOptions,
  getSerumFilterOptions,
  saveSerum,
} from '#/api/serum'
import { SERUM_ERRORS } from '../shared/errors'
import MouseRegistryDialog from '../shared/MouseRegistryDialog.vue'
import AssayMethodEditor from '../shared/AssayMethodEditor.vue'
import SerumUserSelect from '../shared/SerumUserSelect.vue'
import {
  canEditAllSerumProjects,
  canCreateSerumProject,
  canDeleteSerumProject,
  canEditSerumProject,
  getSerumUserName,
} from '#/utils/serumPermission'
import { SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS } from '#/utils/serumMouseOptions'
import {
  SERUM_PROJECT_STATUS_DEFAULT,
  SERUM_PROJECT_STATUS_OPTIONS,
} from '#/utils/serumProjectStatus'
import { shouldRefreshTabData } from '#/utils/staleTabRefresh'

const MIAN_NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

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
  name: 'SerumEdit',
  components: {
    MouseRegistryDialog,
    AssayMethodEditor,
    SerumUserSelect,
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
      loading: false,
      loadFailed: false,
      targetAliasEdit: null,
      targetDisplayNames: {},
      targetLoading: false,
      targetOptions: [],
      targetRequestToken: 0,
      ownerOptions: [],
      pmOptions: [],
      mouseStrainCategoryOptions: SERUM_MOUSE_STRAIN_CATEGORY_OPTIONS,
      projectStatusOptions: SERUM_PROJECT_STATUS_OPTIONS,
      remarkDialogVisible: false,
      currentRemark: '',
      currentRemarkRow: null,
      copyDialogVisible: false,
      copyFromGroup: '',
      copyToGroups: [],
      overwriteSteps: true,
      mouseRegistryDialogVisible: false,
      mouseRegistryEditingRow: null,
      rules: {
          project_code: [{ required: true, message: '必填', trigger: 'blur' }],
          owner: [{ required: true, message: '必填', trigger: 'blur' }]
      },
      activeGroupTab: null,
      groupIdSnapshots: new WeakMap(),
      autoSaveTimer: null,
      autoSaving: false,
      initializing: true,
      applyingServerState: false,
      formRevision: 0,
      savedRevision: 0,
      saveQueued: false,
      savePromise: null,
      loadedRouteIdentity: '',
      initRequestToken: 0,
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
  beforeUnmount() {
    this.clearAutoSaveTimer()
    this.initRequestToken += 1
    this.targetRequestToken += 1
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
      const requestToken = ++this.initRequestToken
      this.targetRequestToken += 1
      this.targetLoading = false
      const routeIdentity = id ? `id:${id}` : 'new'
      let loadSucceeded = false
      this.clearAutoSaveTimer()
      this.loading = Boolean(id)
      this.loadFailed = false
      this.initializing = true
      if (routeIdentity !== this.loadedRouteIdentity) {
        this.postForm = createEmptyPostForm()
        this.targetAliasEdit = null
        this.targetDisplayNames = {}
        this.targetOptions = []
        this.activeGroupTab = null
        this.mouseRegistryEditingRow = null
      }
      try {
        const tasks = [getSerumFilterOptions()]
        if (id) {
          tasks.push(fetchDetail(id))
        }
        const results = await Promise.all(tasks)
        if (requestToken !== this.initRequestToken) return
        const filterOptions = results[0]
        this.ownerOptions = filterOptions?.owners || []
        this.pmOptions = filterOptions?.pms || []
        if (id) {
          const detail = results[1]
          const targetCodes = Array.isArray(detail.target_codes) ? detail.target_codes : []
          this.postForm = { ...detail, target_codes: targetCodes }
          const targetNames = String(detail.target_name || '').split(/[&,]/)
          this.targetDisplayNames = Object.fromEntries(
            targetCodes.map((snum, index) => [snum, targetNames[index] || snum]),
          )
          this.targetOptions = targetCodes.map((snum, index) => ({
            name: targetNames[index] || snum,
            snum,
          }))
          if (targetCodes.length) {
            await this.searchTargetOptions('')
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
          if (this.postForm.mouse_groups.length > 0) {
            this.activeGroupTab = this.postForm.mouse_groups[0].group_id
          }
        } else {
          const currentUser = this.currentUserName
          this.postForm.owner = currentUser.split(' ')[0]
        }
        loadSucceeded = true
      } catch (err) {
        if (requestToken !== this.initRequestToken) return
        this.loadFailed = true
        notifyApiError(err, { messages: SERUM_ERRORS.edit.loadPage })
      } finally {
        if (requestToken !== this.initRequestToken) return
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
    async searchTargetOptions(keyword) {
      const requestToken = ++this.targetRequestToken
      this.targetLoading = true
      try {
        const response = await fetchSerumTargetOptions(keyword, this.postForm.target_codes)
        if (requestToken !== this.targetRequestToken) return
        this.targetOptions = response?.items || []
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
    submitForm(event, isRightClick = false) {
        if (!this.canSaveForm()) {
            ElMessage.warning('您没有权限保存此项目')
            return
        }
        if (this.loading) return
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
                    this.$router.push('/serum/list')
                    setTimeout(() => {
                        this.$router.push('/serum/edit')
                    }, 100)
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
    addMouseGroup() {
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
        // Find smallest available ID (fill gaps first)
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
        this.postForm.antigens.splice(index, 1)
    },
    addTarget() {
        this.postForm.titer_targets.push({ name: '', type: '', species: '', batch_no: '', passage: '', cell_count: '', catalog_no: '', source: '' })
    },
    removeTarget(index) {
        this.postForm.titer_targets.splice(index, 1)
    },
    addPC() {
        this.postForm.titer_pcs.push({ pc_name: '', catalog_batch: '', source: '', concentration: '' })
    },
    removePC(index) {
        this.postForm.titer_pcs.splice(index, 1)
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
    clearAutoSaveTimer() {
      if (!this.autoSaveTimer) return
      clearTimeout(this.autoSaveTimer)
      this.autoSaveTimer = null
    },
    isRevisionConflict(err) {
      const { backendMessage, httpStatus } = extractApiError(err)
      return httpStatus === 409 || String(backendMessage || '').includes('已被其他用户修改')
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
      const mappings = [
        ['mouse_groups', 'new_mouse_records', 'id'],
        ['antigens', 'new_antigen_records', 'id'],
        ['steps', 'new_step_records', 'step_id'],
        ['titer_targets', 'new_target_records', 'id'],
        ['titer_pcs', 'new_pc_records', 'id'],
      ]
      mappings.forEach(([formKey, responseKey, idField]) => {
        const currentRows = this.postForm[formKey] || []
        const pendingRefs = refs[formKey] || []
        const records = response?.[responseKey] || []
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
      if (this.savePromise) return this.savePromise
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
.createPost-main-container {
  padding: 10px 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}
.box-card {
  --el-card-border-color: var(--el-border-color-lighter);
  --el-card-border-radius: 8px;

  margin-bottom: 20px;
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

/* Danger Zone Styling */
.danger-zone-card {
    border: 2px solid #F56C6C;
    background-color: #FEF0F0;
}

.danger-zone-header {
    color: #F56C6C;
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
