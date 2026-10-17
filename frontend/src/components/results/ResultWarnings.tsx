import React from 'react';
import { GenerateResponse } from '../../types';
import { useLanguage } from '../../LanguageContext';
import { productName } from './format';

interface ResultWarningsProps {
  response: GenerateResponse;
}

const noticeClass =
  'rounded-xl border border-yellow-300 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/20 p-4 text-sm text-yellow-800 dark:text-yellow-200';

export const ResultWarnings: React.FC<ResultWarningsProps> = ({ response }) => {
  const { t, language } = useLanguage();
  if (response.warnings.length === 0) return null;

  return (
    <div className="space-y-3">
      {response.warnings.map(warning =>
        warning === 'low_kcal' ? (
          <div key={warning} role="status" className={noticeClass}>
            ⚠️{' '}
            {t(response.kcal_basis === 'menu' ? 'warningLowKcal' : 'warningLowKcalShopping', {
              kcal: Math.round(response.kcal_per_person_day),
            })}
          </div>
        ) : warning === 'kcal_topped_up' ? (
          <div key={warning} role="status" className={noticeClass}>
            ℹ️ {t('warningKcalToppedUp')}
          </div>
        ) : (
          <div key={warning} role="status" className={noticeClass}>
            <p>⚠️ {t('warningBudgetTrimmed')}</p>
            <ul className="mt-2 list-disc pl-6 space-y-0.5">
              {response.trimmed.map(change => (
                <li key={change.product_id}>
                  {productName(change, language)}:{' '}
                  {change.to_packs === 0
                    ? t('trimmedRemoved')
                    : t('trimmedReduced', { from: change.from_packs, to: change.to_packs })}
                </li>
              ))}
            </ul>
          </div>
        )
      )}
    </div>
  );
};
