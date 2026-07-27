import DOMPurify from 'dompurify'
import { marked } from 'marked'

export function renderMarkdown(value: string) {
  const html = marked.parse(String(value || ''), {
    async: false,
    breaks: true,
    gfm: true,
  })

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'a',
      'blockquote',
      'br',
      'code',
      'del',
      'em',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'hr',
      'li',
      'ol',
      'p',
      'pre',
      'strong',
      'table',
      'tbody',
      'td',
      'th',
      'thead',
      'tr',
      'ul',
    ],
    ALLOWED_ATTR: ['class', 'href', 'title'],
  })
}
