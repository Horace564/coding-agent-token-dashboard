// Remove attached context blocks from short labels, keeping the full prompt intact.
export function promptPreview(value, maxLength = 140) {
  const text = String(value ?? '')
    .replace(/<(external_codex_apps_[\w-]+|environment_context)(?:\s[^>]*)?>[\s\S]*?<\/\1\s*>/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return 'Prompt unavailable';
  return text.length > maxLength ? text.slice(0, maxLength - 1) + '…' : text;
}
