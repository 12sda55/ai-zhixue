/**
 * PDF 报告生成 — html2canvas + jsPDF
 */

import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

export async function generatePdf(
  reportEl: HTMLElement,
  onProgress: (pct: number) => void,
): Promise<Blob> {
  onProgress(10)

  // 将报告分节截图
  const sections = reportEl.querySelectorAll('.report-section')
  const canvasList: HTMLCanvasElement[] = []

  // html2canvas 配置
  const canvasOptions = {
    scale: 2,
    useCORS: true,
    backgroundColor: '#ffffff',
    logging: false,
  }

  if (sections.length > 0) {
    for (let i = 0; i < sections.length; i++) {
      const section = sections[i] as HTMLElement
      try {
        const canvas = await html2canvas(section, canvasOptions)
        canvasList.push(canvas)
        onProgress(10 + Math.round((i + 1) / sections.length * 60))
      } catch {
        // 跳过失败的节
      }
    }
  } else {
    // 整体截图
    const canvas = await html2canvas(reportEl, canvasOptions)
    canvasList.push(canvas)
    onProgress(70)
  }

  onProgress(75)

  // 组装 PDF
  const pdf = new jsPDF('p', 'mm', 'a4')
  const pageWidth = 210  // A4 宽度 mm
  const pageHeight = 297 // A4 高度 mm
  const margin = 10

  for (let i = 0; i < canvasList.length; i++) {
    if (i > 0) pdf.addPage()

    const canvas = canvasList[i]
    const imgData = canvas.toDataURL('image/jpeg', 0.95)
    const imgWidth = pageWidth - margin * 2
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    // 如果图片高度超过一页，分页
    let yOffset = 0
    const usableHeight = pageHeight - margin * 2

    if (imgHeight <= usableHeight) {
      pdf.addImage(imgData, 'JPEG', margin, margin, imgWidth, imgHeight)
    } else {
      // 分页渲染
      let remaining = imgHeight
      let page = 0
      while (remaining > 0) {
        if (page > 0) pdf.addPage()
        const sliceHeight = Math.min(remaining, usableHeight)

        // 创建切片 canvas
        const sliceCanvas = document.createElement('canvas')
        sliceCanvas.width = canvas.width
        const slicePixelHeight = (sliceHeight / imgHeight) * canvas.height
        sliceCanvas.height = slicePixelHeight
        const ctx = sliceCanvas.getContext('2d', { willReadFrequently: true })!
        ctx.drawImage(
          canvas,
          0, (yOffset / imgHeight) * canvas.height,
          canvas.width, slicePixelHeight,
          0, 0,
          canvas.width, slicePixelHeight,
        )

        const sliceData = sliceCanvas.toDataURL('image/jpeg', 0.95)
        pdf.addImage(sliceData, 'JPEG', margin, margin, imgWidth, sliceHeight)

        yOffset += sliceHeight
        remaining -= usableHeight
        page++
      }
    }
  }

  onProgress(95)

  const blob = pdf.output('blob')
  onProgress(100)
  return blob
}
