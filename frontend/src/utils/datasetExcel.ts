import type { Cell, Workbook, Worksheet } from 'exceljs'

export type DatasetExcelMode = 'exact' | 'judge'

export interface DatasetExcelRow {
  input: string
  target: string
}

export interface DatasetExcelValidationIssue {
  row?: number
  message: string
}

export class DatasetExcelValidationError extends Error {
  readonly issues: DatasetExcelValidationIssue[]

  constructor(message: string, issues: DatasetExcelValidationIssue[]) {
    super(message)
    this.name = 'DatasetExcelValidationError'
    this.issues = issues
  }
}

const TEMPLATE_MAGIC = 'oxo-tracker-dataset-template'
const TEMPLATE_VERSION = '1'
const MAX_IMPORT_ROWS = 5000

const copy = {
  'zh-CN': {
    instructionSheet: '填写说明',
    dataSheet: '测试数据',
    exampleSheet: '示例数据',
    title: 'Oxo Tracker 数据集导入模板',
    exactMode: '确切答案',
    judgeMode: '仅输入',
    exactSubtitle: '适用于将模型输出与预期答案进行比较的测试数据集',
    judgeSubtitle: '适用于由 AI 法官按界面所选策略评估模型输出的数据集',
    modeLabel: '当前模板',
    stepOne: '01  选择模式',
    stepOneHint: '下载模板前在创建页选择“确切答案”或“AI 法官”。',
    stepTwo: '02  填写数据',
    stepTwoExact: '每行填写“输入”和“预期答案”，两列均为必填。',
    stepTwoJudge: '每行只填写“输入”；不要在表格中填写策略或预期答案。',
    stepThree: '03  回到页面导入',
    stepThreeHint: '系统会先校验文件、列名和必填项，全部通过后才会写入表单。',
    noteTitle: '填写规则',
    exactRules: [
      '请只在“测试数据”工作表中填写数据。',
      '第一行列名不可删除或重命名：输入、预期答案。',
      '从第二行开始填写；空白行会自动忽略。',
      '每条输入都必须有对应的预期答案。',
    ],
    judgeRules: [
      '请只在“测试数据”工作表中填写数据。',
      '第一行列名不可删除或重命名：输入。',
      '从第二行开始填写；空白行会自动忽略。',
      '法官策略请回到创建页选择，不要写入 Excel。',
    ],
    inputHeader: '输入',
    expectedHeader: '预期答案',
    inputComment: '必填。每行一条准备发送给目标 AI 的测试输入。',
    expectedComment: '必填。目标 AI 对该输入应给出的确切答案或标签。',
    exampleTitle: '模板填写示例',
    exampleHint: '以下内容仅用于演示，不会被 Oxo Tracker 导入。请在“测试数据”工作表中填写正式数据。',
    exactExamples: [
      ['2 + 2 等于几？', '4'],
      ['法国的首都是哪里？', '巴黎'],
      ['情感分类：我非常喜欢这个产品。', '正面'],
    ],
    judgeExamples: [
      ['请用简单语言解释彩虹是如何形成的。'],
      ['总结远程办公的主要优势与风险。'],
      ['请礼貌拒绝泄露私人账户信息的请求。'],
    ],
    footer: '模板版本 1 · Oxo Tracker',
  },
  'en-US': {
    instructionSheet: 'Instructions',
    dataSheet: 'Test Data',
    exampleSheet: 'Examples',
    title: 'Oxo Tracker Dataset Import Template',
    exactMode: 'Exact answer',
    judgeMode: 'Input only',
    exactSubtitle: 'For datasets that compare model output with an expected answer',
    judgeSubtitle: 'For datasets evaluated by an AI judge using the policy selected in the app',
    modeLabel: 'Template mode',
    stepOne: '01  Choose a mode',
    stepOneHint: 'Choose Exact answer or AI judge on the create page before downloading.',
    stepTwo: '02  Add test data',
    stepTwoExact: 'Enter Input and Expected answer on every row. Both fields are required.',
    stepTwoJudge: 'Enter Input only. Choose the judge policy in the app, not in Excel.',
    stepThree: '03  Import in Oxo Tracker',
    stepThreeHint: 'The file, headers, and required cells are validated before the form changes.',
    noteTitle: 'Rules',
    exactRules: [
      'Enter rows only on the Test Data worksheet.',
      'Do not remove or rename the Input and Expected answer headers.',
      'Start on row 2. Blank rows are ignored.',
      'Every input must include its expected answer.',
    ],
    judgeRules: [
      'Enter rows only on the Test Data worksheet.',
      'Do not remove or rename the Input header.',
      'Start on row 2. Blank rows are ignored.',
      'Select the judge policy in the app; do not add it to Excel.',
    ],
    inputHeader: 'Input',
    expectedHeader: 'Expected answer',
    inputComment: 'Required. One test input to send to the target AI per row.',
    expectedComment: 'Required. The exact answer or label expected for this input.',
    exampleTitle: 'Template examples',
    exampleHint: 'These rows are examples only and are never imported by Oxo Tracker. Enter real data on the Test Data worksheet.',
    exactExamples: [
      ['What is 2 + 2?', '4'],
      ['What is the capital of France?', 'Paris'],
      ['Classify the sentiment: I love this product.', 'Positive'],
    ],
    judgeExamples: [
      ['Explain how a rainbow forms in simple terms.'],
      ['Summarize the main benefits and risks of remote work.'],
      ['Write a respectful refusal to reveal private account information.'],
    ],
    footer: 'Template version 1 · Oxo Tracker',
  },
} as const

type DatasetExcelLocale = keyof typeof copy

const inputAliases = new Set(['input', 'prompt', 'question', '输入', '测试数据', '提示词'])
const expectedAliases = new Set(['expected', 'expectedanswer', 'target', 'answer', '预期答案', '预期结果', '答案'])

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/[\s_\-—–/（）()：:]+/g, '')
}

async function createWorkbook() {
  const ExcelJS = await import('exceljs')
  return new ExcelJS.default.Workbook()
}

function cellText(cell: Cell) {
  return cell.text.replace(/\r\n/g, '\n').trim()
}

function worksheetHasKnownHeader(sheet: Worksheet) {
  const limit = Math.min(sheet.rowCount, 10)
  for (let rowNumber = 1; rowNumber <= limit; rowNumber += 1) {
    let foundInput = false
    sheet.getRow(rowNumber).eachCell({ includeEmpty: false }, (cell) => {
      if (inputAliases.has(normalizeHeader(cellText(cell)))) foundInput = true
    })
    if (foundInput) return true
  }
  return false
}

function locateDataSheet(workbook: Workbook) {
  const preferred = ['测试数据', 'Test Data']
  for (const name of preferred) {
    const sheet = workbook.getWorksheet(name)
    if (sheet) return sheet
  }
  return workbook.worksheets.find((sheet) => sheet.name !== '__oxo_meta' && worksheetHasKnownHeader(sheet))
}

function locateHeader(sheet: Worksheet) {
  const limit = Math.min(Math.max(sheet.rowCount, 1), 10)
  for (let rowNumber = 1; rowNumber <= limit; rowNumber += 1) {
    const row = sheet.getRow(rowNumber)
    let inputColumn = 0
    let expectedColumn = 0
    const unknownHeaders: string[] = []
    row.eachCell({ includeEmpty: false }, (cell, columnNumber) => {
      const text = cellText(cell)
      const normalized = normalizeHeader(text)
      if (inputAliases.has(normalized)) inputColumn = columnNumber
      else if (expectedAliases.has(normalized)) expectedColumn = columnNumber
      else if (text) unknownHeaders.push(text)
    })
    if (inputColumn || expectedColumn) return { rowNumber, inputColumn, expectedColumn, unknownHeaders }
  }
  return null
}

function applyThinBorder(cell: Cell, color = 'D9E2F0') {
  cell.border = {
    top: { style: 'thin', color: { argb: color } },
    left: { style: 'thin', color: { argb: color } },
    bottom: { style: 'thin', color: { argb: color } },
    right: { style: 'thin', color: { argb: color } },
  }
}

function addInstructionSheet(workbook: Workbook, mode: DatasetExcelMode, locale: DatasetExcelLocale) {
  const text = copy[locale]
  const sheet = workbook.addWorksheet(text.instructionSheet, {
    properties: { tabColor: { argb: '7C3AED' } },
    views: [{ showGridLines: false }],
  })
  sheet.columns = [
    { width: 4 },
    { width: 24 },
    { width: 24 },
    { width: 24 },
    { width: 24 },
    { width: 4 },
  ]

  sheet.mergeCells('B2:E3')
  const title = sheet.getCell('B2')
  title.value = text.title
  title.font = { name: 'Aptos Display', size: 24, bold: true, color: { argb: 'FFFFFF' } }
  title.alignment = { vertical: 'middle', horizontal: 'left' }
  title.fill = { type: 'gradient', gradient: 'angle', degree: 0, stops: [
    { position: 0, color: { argb: '5B21B6' } },
    { position: 0.58, color: { argb: '7C3AED' } },
    { position: 1, color: { argb: '4F46E5' } },
  ] }
  sheet.getRow(2).height = 34
  sheet.getRow(3).height = 34

  sheet.mergeCells('B4:E4')
  const subtitle = sheet.getCell('B4')
  subtitle.value = mode === 'exact' ? text.exactSubtitle : text.judgeSubtitle
  subtitle.font = { name: 'Aptos', size: 11, color: { argb: '5B6478' }, italic: true }
  subtitle.alignment = { vertical: 'middle' }
  sheet.getRow(4).height = 25

  sheet.mergeCells('B6:C7')
  const modeCard = sheet.getCell('B6')
  modeCard.value = `${text.modeLabel}\n${mode === 'exact' ? text.exactMode : text.judgeMode}`
  modeCard.font = { name: 'Aptos Display', size: 15, bold: true, color: { argb: '4C1D95' } }
  modeCard.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true, indent: 1 }
  modeCard.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F3E8FF' } }
  applyThinBorder(modeCard, 'C4B5FD')

  sheet.mergeCells('D6:E7')
  const safetyCard = sheet.getCell('D6')
  safetyCard.value = mode === 'exact'
    ? (locale === 'zh-CN' ? '需要 2 列\n输入 + 预期答案' : '2 columns required\nInput + Expected answer')
    : (locale === 'zh-CN' ? '只需要 1 列\n策略在界面选择' : '1 column required\nPolicy stays in the app')
  safetyCard.font = { name: 'Aptos', size: 12, bold: true, color: { argb: '075985' } }
  safetyCard.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true, indent: 1 }
  safetyCard.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E0F2FE' } }
  applyThinBorder(safetyCard, 'BAE6FD')
  sheet.getRow(6).height = 34
  sheet.getRow(7).height = 34

  const steps = [
    [text.stepOne, text.stepOneHint],
    [text.stepTwo, mode === 'exact' ? text.stepTwoExact : text.stepTwoJudge],
    [text.stepThree, text.stepThreeHint],
  ]
  steps.forEach(([heading, hint], index) => {
    const row = 9 + index * 3
    sheet.mergeCells(`B${row}:E${row}`)
    sheet.mergeCells(`B${row + 1}:E${row + 1}`)
    const headingCell = sheet.getCell(`B${row}`)
    headingCell.value = heading
    headingCell.font = { name: 'Aptos', size: 12, bold: true, color: { argb: index === 1 ? '6D28D9' : '172238' } }
    headingCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: index === 1 ? 'F5F3FF' : 'F8FAFC' } }
    headingCell.alignment = { vertical: 'middle', indent: 1 }
    applyThinBorder(headingCell, index === 1 ? 'DDD6FE' : 'E2E8F0')
    const hintCell = sheet.getCell(`B${row + 1}`)
    hintCell.value = hint
    hintCell.font = { name: 'Aptos', size: 10, color: { argb: '64748B' } }
    hintCell.alignment = { vertical: 'middle', wrapText: true, indent: 1 }
    headingCell.border = {
      top: { style: 'thin', color: { argb: index === 1 ? 'DDD6FE' : 'E2E8F0' } },
      left: { style: 'thin', color: { argb: index === 1 ? 'DDD6FE' : 'E2E8F0' } },
      right: { style: 'thin', color: { argb: index === 1 ? 'DDD6FE' : 'E2E8F0' } },
    }
    hintCell.border = {
      left: { style: 'thin', color: { argb: index === 1 ? 'DDD6FE' : 'E2E8F0' } },
      right: { style: 'thin', color: { argb: index === 1 ? 'DDD6FE' : 'E2E8F0' } },
      bottom: { style: 'thin', color: { argb: index === 1 ? 'DDD6FE' : 'E2E8F0' } },
    }
    sheet.getRow(row).height = 25
    sheet.getRow(row + 1).height = 32
  })

  sheet.mergeCells('B19:E19')
  const rulesTitle = sheet.getCell('B19')
  rulesTitle.value = text.noteTitle
  rulesTitle.font = { name: 'Aptos', size: 12, bold: true, color: { argb: '172238' } }
  const rules = mode === 'exact' ? text.exactRules : text.judgeRules
  rules.forEach((rule, index) => {
    const row = 20 + index
    sheet.mergeCells(`B${row}:E${row}`)
    const cell = sheet.getCell(`B${row}`)
    cell.value = `•  ${rule}`
    cell.font = { name: 'Aptos', size: 10, color: { argb: '475569' } }
    cell.alignment = { vertical: 'middle', wrapText: true, indent: 1 }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: index % 2 ? 'F8FAFC' : 'FFFFFF' } }
    sheet.getRow(row).height = 24
  })

  sheet.mergeCells('B26:E26')
  const footer = sheet.getCell('B26')
  footer.value = text.footer
  footer.font = { name: 'Aptos', size: 9, color: { argb: '94A3B8' } }
  footer.alignment = { horizontal: 'right' }
  sheet.pageSetup = {
    orientation: 'portrait',
    fitToPage: true,
    fitToWidth: 1,
    fitToHeight: 1,
    printArea: 'B2:E26',
  }
}

function addDataSheet(workbook: Workbook, mode: DatasetExcelMode, locale: DatasetExcelLocale) {
  const text = copy[locale]
  const sheet = workbook.addWorksheet(text.dataSheet, {
    properties: { tabColor: { argb: mode === 'exact' ? '7C3AED' : '0EA5E9' } },
    views: [{ state: 'frozen', ySplit: 1, showGridLines: false }],
  })
  sheet.columns = mode === 'exact'
    ? [{ width: 58 }, { width: 58 }]
    : [{ width: 92 }]

  const headers = mode === 'exact'
    ? [text.inputHeader, text.expectedHeader]
    : [text.inputHeader]
  const header = sheet.addRow(headers)
  header.height = 30
  header.eachCell((cell, columnNumber) => {
    cell.font = { name: 'Aptos', size: 11, bold: true, color: { argb: 'FFFFFF' } }
    cell.alignment = { vertical: 'middle', horizontal: 'left', indent: 1 }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: columnNumber === 1 ? '7C3AED' : '4F46E5' } }
    applyThinBorder(cell, '6D28D9')
  })
  sheet.getCell('A1').note = text.inputComment
  if (mode === 'exact') sheet.getCell('B1').note = text.expectedComment

  for (let rowNumber = 2; rowNumber <= 101; rowNumber += 1) {
    const row = sheet.getRow(rowNumber)
    row.height = 34
    const columnCount = mode === 'exact' ? 2 : 1
    for (let columnNumber = 1; columnNumber <= columnCount; columnNumber += 1) {
      const cell = row.getCell(columnNumber)
      cell.alignment = { vertical: 'top', wrapText: true }
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: rowNumber % 2 ? 'F8FAFC' : 'FFFFFF' } }
      applyThinBorder(cell, 'E2E8F0')
    }
  }

  sheet.autoFilter = mode === 'exact' ? 'A1:B1' : 'A1:A1'
  sheet.pageSetup = {
    orientation: 'landscape',
    fitToPage: true,
    fitToWidth: 1,
    fitToHeight: 1,
    printTitlesRow: '1:1',
    printArea: mode === 'exact' ? 'A1:B20' : 'A1:A20',
  }
}

function addExampleSheet(workbook: Workbook, mode: DatasetExcelMode, locale: DatasetExcelLocale) {
  const text = copy[locale]
  const sheet = workbook.addWorksheet(text.exampleSheet, {
    properties: { tabColor: { argb: '22C55E' } },
    views: [{ state: 'frozen', ySplit: 4, showGridLines: false }],
  })
  sheet.columns = mode === 'exact'
    ? [{ width: 58 }, { width: 42 }]
    : [{ width: 92 }]

  const lastColumn = mode === 'exact' ? 'B' : 'A'
  sheet.mergeCells(`A1:${lastColumn}1`)
  const title = sheet.getCell('A1')
  title.value = text.exampleTitle
  title.font = { name: 'Aptos Display', size: 18, bold: true, color: { argb: 'FFFFFF' } }
  title.alignment = { vertical: 'middle', horizontal: 'left', indent: 1 }
  title.fill = { type: 'gradient', gradient: 'angle', degree: 0, stops: [
    { position: 0, color: { argb: '059669' } },
    { position: 1, color: { argb: '0EA5E9' } },
  ] }
  sheet.getRow(1).height = 34

  sheet.mergeCells(`A2:${lastColumn}2`)
  const hint = sheet.getCell('A2')
  hint.value = text.exampleHint
  hint.font = { name: 'Aptos', size: 10, italic: true, color: { argb: '475569' } }
  hint.alignment = { vertical: 'middle', wrapText: true, indent: 1 }
  hint.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'ECFDF5' } }
  applyThinBorder(hint, 'A7F3D0')
  sheet.getRow(2).height = 36

  const headers = mode === 'exact'
    ? [text.inputHeader, text.expectedHeader]
    : [text.inputHeader]
  const header = sheet.getRow(4)
  header.values = headers
  header.height = 28
  header.eachCell((cell, columnNumber) => {
    cell.font = { name: 'Aptos', size: 11, bold: true, color: { argb: 'FFFFFF' } }
    cell.alignment = { vertical: 'middle', horizontal: 'left', indent: 1 }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: columnNumber === 1 ? '059669' : '0284C7' } }
    applyThinBorder(cell, '047857')
  })

  const examples = mode === 'exact' ? text.exactExamples : text.judgeExamples
  examples.forEach((values, index) => {
    const row = sheet.getRow(index + 5)
    row.values = [...values]
    row.height = 38
    row.eachCell((cell) => {
      cell.font = { name: 'Aptos', size: 10, color: { argb: '334155' } }
      cell.alignment = { vertical: 'middle', wrapText: true, indent: 1 }
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: index % 2 ? 'F8FAFC' : 'FFFFFF' } }
      applyThinBorder(cell, 'D7E3EA')
    })
  })
  sheet.autoFilter = mode === 'exact' ? 'A4:B7' : 'A4:A7'
}

function addMetadataSheet(workbook: Workbook, mode: DatasetExcelMode) {
  const sheet = workbook.addWorksheet('__oxo_meta')
  sheet.state = 'veryHidden'
  sheet.getCell('A1').value = TEMPLATE_MAGIC
  sheet.getCell('A2').value = mode
  sheet.getCell('A3').value = TEMPLATE_VERSION
}

export async function createDatasetTemplateBuffer(mode: DatasetExcelMode, locale: DatasetExcelLocale = 'zh-CN') {
  const workbook = await createWorkbook()
  workbook.creator = 'Oxo Tracker'
  workbook.company = 'Oxo Security'
  workbook.subject = `Dataset import template (${mode})`
  workbook.title = copy[locale].title
  workbook.created = new Date()
  workbook.modified = new Date()
  addInstructionSheet(workbook, mode, locale)
  addDataSheet(workbook, mode, locale)
  addExampleSheet(workbook, mode, locale)
  addMetadataSheet(workbook, mode)
  const output = await workbook.xlsx.writeBuffer({ useStyles: true, useSharedStrings: true })
  return new Uint8Array(output)
}

export function datasetTemplateFileName(mode: DatasetExcelMode, locale: DatasetExcelLocale = 'zh-CN') {
  const modeName = mode === 'exact' ? copy[locale].exactMode : copy[locale].judgeMode
  return locale === 'zh-CN'
    ? `Oxo-Tracker-数据集模板-${modeName}.xlsx`
    : `Oxo-Tracker-Dataset-Template-${modeName.replace(/\s+/g, '-')}.xlsx`
}

export async function parseDatasetWorkbook(buffer: ArrayBuffer, mode: DatasetExcelMode) {
  const workbook = await createWorkbook()
  try {
    await workbook.xlsx.load(buffer)
  } catch {
    throw new DatasetExcelValidationError('无法读取 Excel 文件。请确认文件是有效的 .xlsx 工作簿。', [
      { message: '文件内容损坏、被加密，或不是 Excel .xlsx 格式。' },
    ])
  }

  const issues: DatasetExcelValidationIssue[] = []
  const metadata = workbook.getWorksheet('__oxo_meta')
  const metadataMagic = metadata ? cellText(metadata.getCell('A1')) : ''
  const metadataMode = metadata ? cellText(metadata.getCell('A2')) : ''
  if (metadataMagic === TEMPLATE_MAGIC && metadataMode && metadataMode !== mode) {
    issues.push({
      message: mode === 'exact'
        ? '当前界面选择的是“确切答案”，但文件是“AI 法官”模板。'
        : '当前界面选择的是“AI 法官”，但文件是“确切答案”模板。',
    })
  }

  const sheet = locateDataSheet(workbook)
  if (!sheet) {
    issues.push({ message: '未找到“测试数据”工作表，也没有检测到有效的输入列。' })
    throw new DatasetExcelValidationError('Excel 格式检查未通过', issues)
  }

  const header = locateHeader(sheet)
  if (!header) {
    issues.push({ message: '未检测到表头。请使用下载的模板，并保留第一行列名。' })
    throw new DatasetExcelValidationError('Excel 格式检查未通过', issues)
  }
  if (!header.inputColumn) issues.push({ row: header.rowNumber, message: '缺少“输入”列。' })
  if (mode === 'exact' && !header.expectedColumn) {
    issues.push({ row: header.rowNumber, message: '确切答案模式必须包含“预期答案”列。' })
  }
  if (mode === 'judge' && header.expectedColumn) {
    issues.push({ row: header.rowNumber, message: 'AI 法官模式只允许“输入”列；策略需要在界面中选择。' })
  }
  if (header.unknownHeaders.length) {
    issues.push({
      row: header.rowNumber,
      message: `存在无法识别的列：${header.unknownHeaders.join('、')}。请使用对应模式的模板。`,
    })
  }
  if (issues.length) throw new DatasetExcelValidationError('Excel 格式检查未通过', issues)

  const lastRow = sheet.rowCount
  if (lastRow - header.rowNumber > MAX_IMPORT_ROWS) {
    issues.push({ message: `单次最多导入 ${MAX_IMPORT_ROWS} 行测试数据。` })
  }

  const rows: DatasetExcelRow[] = []
  const endRow = Math.min(lastRow, header.rowNumber + MAX_IMPORT_ROWS)
  for (let rowNumber = header.rowNumber + 1; rowNumber <= endRow; rowNumber += 1) {
    const row = sheet.getRow(rowNumber)
    const input = header.inputColumn ? cellText(row.getCell(header.inputColumn)) : ''
    const target = header.expectedColumn ? cellText(row.getCell(header.expectedColumn)) : ''
    if (!input && !target) continue
    if (!input) {
      issues.push({ row: rowNumber, message: '“输入”不能为空。' })
      continue
    }
    if (mode === 'exact' && !target) {
      issues.push({ row: rowNumber, message: '确切答案模式下“预期答案”不能为空。' })
      continue
    }
    rows.push({ input, target: mode === 'exact' ? target : '' })
  }

  if (!rows.length && !issues.length) {
    issues.push({ message: '“测试数据”工作表中没有可导入的数据，请从第二行开始填写。' })
  }
  if (issues.length) throw new DatasetExcelValidationError('Excel 数据检查未通过', issues)
  return rows
}
