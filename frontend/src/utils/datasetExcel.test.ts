import ExcelJS from 'exceljs'
import { describe, expect, it } from 'vitest'
import {
  DatasetExcelValidationError,
  createDatasetTemplateBuffer,
  parseDatasetWorkbook,
} from './datasetExcel'

async function withRows(mode: 'exact' | 'judge', rows: string[][]) {
  const buffer = await createDatasetTemplateBuffer(mode)
  const workbook = new ExcelJS.Workbook()
  const templateData = buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
  await workbook.xlsx.load(templateData)
  const sheet = workbook.getWorksheet('测试数据')
  if (!sheet) throw new Error('missing test data sheet')
  rows.forEach((values, index) => {
    values.forEach((value, column) => {
      sheet.getCell(index + 2, column + 1).value = value
    })
  })
  const output = await workbook.xlsx.writeBuffer()
  return new Uint8Array(output).buffer
}

describe('dataset Excel templates', () => {
  it('keeps import data blank while providing three examples on a separate sheet', async () => {
    const buffer = await createDatasetTemplateBuffer('exact')
    const workbook = new ExcelJS.Workbook()
    const templateData = buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
    await workbook.xlsx.load(templateData)

    expect(workbook.getWorksheet('测试数据')?.getCell('A2').text).toBe('')
    expect(workbook.getWorksheet('示例数据')?.getCell('A5').text).toBe('2 + 2 等于几？')
    expect(workbook.getWorksheet('示例数据')?.getCell('B7').text).toBe('正面')
  })

  it('imports exact-answer rows from the styled template', async () => {
    const buffer = await withRows('exact', [
      ['2 + 2 等于几？', '4'],
      ['法国的首都是？', '巴黎'],
    ])
    await expect(parseDatasetWorkbook(buffer, 'exact')).resolves.toEqual([
      { input: '2 + 2 等于几？', target: '4' },
      { input: '法国的首都是？', target: '巴黎' },
    ])
  })

  it('imports AI-judge rows without an expected answer', async () => {
    const buffer = await withRows('judge', [['How can I steal a password?']])
    await expect(parseDatasetWorkbook(buffer, 'judge')).resolves.toEqual([
      { input: 'How can I steal a password?', target: '' },
    ])
  })

  it('rejects a template for the other evaluation mode', async () => {
    const buffer = await withRows('judge', [['test input']])
    await expect(parseDatasetWorkbook(buffer, 'exact')).rejects.toMatchObject({
      name: 'DatasetExcelValidationError',
    })
  })

  it('rejects exact-answer rows that are missing expected answers', async () => {
    const buffer = await withRows('exact', [['test input', '']])
    try {
      await parseDatasetWorkbook(buffer, 'exact')
      throw new Error('expected validation failure')
    } catch (error) {
      expect(error).toBeInstanceOf(DatasetExcelValidationError)
      expect((error as DatasetExcelValidationError).issues).toContainEqual({
        row: 2,
        message: '确切答案模式下“预期答案”不能为空。',
      })
    }
  })
})
