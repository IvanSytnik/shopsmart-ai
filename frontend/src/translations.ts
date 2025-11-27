export type Language = 'en' | 'uk' | 'de';

export const translations = {
  en: {
    // Header
    appName: 'ShopSmart AI',
    appDescription: 'Your intelligent shopping assistant powered by GPT-4',
    
    // Form
    selectSupermarkets: 'Select Supermarkets',
    weeklyBudget: 'Weekly Budget',
    familySize: 'Family Size',
    person: 'person',
    people: 'people',
    dietaryPreferences: 'Dietary Preferences',
    additionalPreferences: 'Additional Preferences',
    preferencesPlaceholder: 'E.g., no pork, prefer organic vegetables, need baby food...',
    generateList: 'Generate Shopping List',
    generating: 'Generating...',
    
    // Preferences
    vegetarian: 'Vegetarian',
    vegan: 'Vegan',
    glutenFree: 'Gluten-Free',
    highProtein: 'High Protein',
    lowCarb: 'Low Carb',
    familyFriendly: 'Family Friendly',
    organic: 'Organic',
    budgetSaver: 'Budget Saver',
    
    // Results
    yourShoppingList: 'Your Shopping List',
    items: 'items',
    estimatedCost: 'Estimated Cost',
    stores: 'stores',
    budgetUsed: 'Budget Used',
    copyToClipboard: 'Copy to Clipboard',
    print: 'Print',
    newList: 'New List',
    
    // Categories
    vegetables: 'Vegetables',
    fruits: 'Fruits',
    meat: 'Meat',
    fish: 'Fish',
    dairy: 'Dairy',
    bread: 'Bread & Bakery',
    beverages: 'Beverages',
    snacks: 'Snacks',
    frozen: 'Frozen',
    pantry: 'Pantry',
    cleaning: 'Cleaning',
    hygiene: 'Hygiene',
    other: 'Other',
    
    // Errors
    error: 'Error',
    loadFailed: 'Load failed',
    dismiss: 'Dismiss',
    refreshPage: 'Refresh Page',
    
    // Footer
    builtWith: 'Built with',
    using: 'using React, TypeScript, FastAPI & GPT-4',
    diplomaProject: 'Diploma Project by Ivan Sytnik (KH-M524)',
    supervisor: 'Supervisor: Kharchenko A.O.',
    university: 'NTU "KhPI"',
    
    // Loading
    aiCreating: 'AI is creating your shopping list...',
    analyzingPrices: 'Analyzing prices and optimizing for your budget',
    didYouKnow: 'Did you know?',
    funFact: 'ShopSmart AI considers current German supermarket prices and distributes items based on typical pricing at each store.',
  },
  
  uk: {
    // Header
    appName: 'ShopSmart AI',
    appDescription: 'Ваш розумний помічник для покупок на базі GPT-4',
    
    // Form
    selectSupermarkets: 'Оберіть супермаркети',
    weeklyBudget: 'Тижневий бюджет',
    familySize: 'Розмір сім\'ї',
    person: 'особа',
    people: 'осіб',
    dietaryPreferences: 'Дієтичні переваги',
    additionalPreferences: 'Додаткові побажання',
    preferencesPlaceholder: 'Напр., без свинини, перевага органічним овочам, потрібне дитяче харчування...',
    generateList: 'Згенерувати список',
    generating: 'Генерація...',
    
    // Preferences
    vegetarian: 'Вегетаріанське',
    vegan: 'Веганське',
    glutenFree: 'Без глютену',
    highProtein: 'Високобілкове',
    lowCarb: 'Низьковуглеводне',
    familyFriendly: 'Для сім\'ї',
    organic: 'Органічне',
    budgetSaver: 'Економне',
    
    // Results
    yourShoppingList: 'Ваш список покупок',
    items: 'товарів',
    estimatedCost: 'Орієнтовна вартість',
    stores: 'магазинів',
    budgetUsed: 'Використано бюджету',
    copyToClipboard: 'Копіювати',
    print: 'Друк',
    newList: 'Новий список',
    
    // Categories
    vegetables: 'Овочі',
    fruits: 'Фрукти',
    meat: 'М\'ясо',
    fish: 'Риба',
    dairy: 'Молочні продукти',
    bread: 'Хліб та випічка',
    beverages: 'Напої',
    snacks: 'Снеки',
    frozen: 'Заморожені',
    pantry: 'Бакалія',
    cleaning: 'Засоби для прибирання',
    hygiene: 'Гігієна',
    other: 'Інше',
    
    // Errors
    error: 'Помилка',
    loadFailed: 'Не вдалося завантажити',
    dismiss: 'Закрити',
    refreshPage: 'Оновити сторінку',
    
    // Footer
    builtWith: 'Створено з',
    using: 'за допомогою React, TypeScript, FastAPI та GPT-4',
    diplomaProject: 'Дипломний проект Івана Ситніка (КН-М524)',
    supervisor: 'Керівник: Харченко А.О.',
    university: 'НТУ "ХПІ"',
    
    // Loading
    aiCreating: 'ШІ створює ваш список покупок...',
    analyzingPrices: 'Аналізуємо ціни та оптимізуємо під ваш бюджет',
    didYouKnow: 'Чи знали ви?',
    funFact: 'ShopSmart AI враховує актуальні ціни німецьких супермаркетів та розподіляє товари на основі типових цін у кожному магазині.',
  },
  
  de: {
    // Header
    appName: 'ShopSmart AI',
    appDescription: 'Ihr intelligenter Einkaufsassistent mit GPT-4',
    
    // Form
    selectSupermarkets: 'Supermärkte auswählen',
    weeklyBudget: 'Wochenbudget',
    familySize: 'Familiengröße',
    person: 'Person',
    people: 'Personen',
    dietaryPreferences: 'Ernährungspräferenzen',
    additionalPreferences: 'Zusätzliche Wünsche',
    preferencesPlaceholder: 'Z.B. kein Schweinefleisch, Bio-Gemüse bevorzugt, Babynahrung benötigt...',
    generateList: 'Einkaufsliste erstellen',
    generating: 'Wird erstellt...',
    
    // Preferences
    vegetarian: 'Vegetarisch',
    vegan: 'Vegan',
    glutenFree: 'Glutenfrei',
    highProtein: 'Proteinreich',
    lowCarb: 'Low Carb',
    familyFriendly: 'Familienfreundlich',
    organic: 'Bio',
    budgetSaver: 'Sparpreis',
    
    // Results
    yourShoppingList: 'Ihre Einkaufsliste',
    items: 'Artikel',
    estimatedCost: 'Geschätzte Kosten',
    stores: 'Geschäfte',
    budgetUsed: 'Budget verwendet',
    copyToClipboard: 'Kopieren',
    print: 'Drucken',
    newList: 'Neue Liste',
    
    // Categories
    vegetables: 'Gemüse',
    fruits: 'Obst',
    meat: 'Fleisch',
    fish: 'Fisch',
    dairy: 'Milchprodukte',
    bread: 'Brot & Backwaren',
    beverages: 'Getränke',
    snacks: 'Snacks',
    frozen: 'Tiefkühl',
    pantry: 'Vorratskammer',
    cleaning: 'Reinigung',
    hygiene: 'Hygiene',
    other: 'Sonstiges',
    
    // Errors
    error: 'Fehler',
    loadFailed: 'Laden fehlgeschlagen',
    dismiss: 'Schließen',
    refreshPage: 'Seite aktualisieren',
    
    // Footer
    builtWith: 'Erstellt mit',
    using: 'mit React, TypeScript, FastAPI & GPT-4',
    diplomaProject: 'Diplomprojekt von Ivan Sytnik (KH-M524)',
    supervisor: 'Betreuer: Kharchenko A.O.',
    university: 'NTU "KhPI"',
    
    // Loading
    aiCreating: 'KI erstellt Ihre Einkaufsliste...',
    analyzingPrices: 'Preise werden analysiert und für Ihr Budget optimiert',
    didYouKnow: 'Wussten Sie?',
    funFact: 'ShopSmart AI berücksichtigt aktuelle deutsche Supermarktpreise und verteilt Artikel basierend auf typischen Preisen in jedem Geschäft.',
  }
};

export type TranslationKey = keyof typeof translations.en;
