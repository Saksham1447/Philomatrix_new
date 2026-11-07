export function formatAttendancePercentage(value: unknown): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return '0.00';
  }

  const rounded = Math.round((numericValue + Number.EPSILON) * 100) / 100;
  return rounded.toFixed(2);
}
