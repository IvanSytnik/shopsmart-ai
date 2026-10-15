import React from 'react';
import { DayMenu, GenerateResponse } from '../types';
import { useLanguage } from '../LanguageContext';
import { itemsById, nameFromId, trimmedName } from './results/format';

interface MealPlanProps {
  response: GenerateResponse;
  menu: DayMenu[];
}

const MEALS = [
  ['breakfast', '🌅'],
  ['lunch', '☀️'],
  ['dinner', '🌙'],
  ['snack', '🍎'],
] as const;

export const MealPlan: React.FC<MealPlanProps> = ({ response, menu }) => {
  const { t } = useLanguage();
  const items = itemsById(response);
  const trimmed = new Map(response.trimmed.map(change => [change.product_id, change]));
  const removedName = (id: string) => {
    const change = trimmed.get(id);
    return change ? trimmedName(change) : nameFromId(id);
  };

  return (
    <div className="space-y-4">
      {menu.map((day, idx) => (
        <section
          key={idx}
          aria-label={day.day}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden transition-colors"
        >
          <div className="bg-gradient-to-r from-primary-500 to-purple-600 px-6 py-4">
            <h3 className="text-lg font-semibold text-white">{day.day}</h3>
          </div>
          <div className="p-4 space-y-3">
            {MEALS.map(([slot, icon]) => {
              const meal = day[slot];
              if (!meal) return null;
              return (
                <div
                  key={slot}
                  className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl"
                >
                  <span className="text-2xl">{icon}</span>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {t(slot)}
                    </div>
                    <div className="font-medium text-gray-800 dark:text-gray-200">{meal.name}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {meal.description}
                    </div>
                    {meal.ingredient_ids.length > 0 && (
                      <ul className="mt-2 flex flex-wrap gap-1.5 text-xs">
                        {meal.ingredient_ids.map(id => {
                          const item = items.get(id);
                          return item ? (
                            <li
                              key={id}
                              className="px-2 py-0.5 rounded-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                            >
                              {item.name}
                            </li>
                          ) : (
                            <li
                              key={id}
                              className="px-2 py-0.5 rounded-full border border-dashed border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500"
                            >
                              <s>{removedName(id)}</s> {t('removedBudget')}
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
};
