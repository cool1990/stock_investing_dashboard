export function createToggleChip(
  label: string,
  checked: boolean,
  onChange: (next: boolean) => void,
  disabled = false,
): HTMLElement {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'toggle-chip';
  btn.setAttribute('aria-pressed', String(checked && !disabled));
  btn.setAttribute('aria-disabled', String(disabled));
  btn.textContent = checked && !disabled ? `✓ ${label}` : label;
  if (disabled) btn.classList.add('is-disabled');
  btn.addEventListener('click', () => {
    if (btn.getAttribute('aria-disabled') === 'true') return;
    const next = btn.getAttribute('aria-pressed') !== 'true';
    btn.setAttribute('aria-pressed', String(next));
    btn.textContent = next ? `✓ ${label}` : label;
    onChange(next);
  });
  return btn;
}
