// Shared by the plan form and the compare form.

// Group captions are <p>s named by aria-labelledby: a <label> must point at one field.
export const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3';

export const chipClass = (selected: boolean) =>
  `flex items-center gap-1 px-3 py-2 rounded-lg border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
    selected
      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
      : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
  }`;

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter(v => v !== value) : [...list, value];
}
