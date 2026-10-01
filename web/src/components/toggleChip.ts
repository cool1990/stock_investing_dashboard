export function createToggleChip(
  label: string,
  checked: boolean,
  onChange: (next: boolean) => void,
  disabled = false,
): HTMLElement {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'toggle-chip';
  btn.setAttribute('aria-pressed', String(checked));
  btn.disabled = disabled;
  btn.textContent = checked ? `✓ ${label}` : label;
  if (disabled) btn.classList.add('is-disabled');
  btn.addEventListener('click', () => {
    const next = btn.getAttribute('aria-pressed') !== 'true';
    btn.setAttribute('aria-pressed', String(next));
    btn.textContent = next ? `✓ ${label}` : label;
    onChange(next);
  });
  return btn;
}
