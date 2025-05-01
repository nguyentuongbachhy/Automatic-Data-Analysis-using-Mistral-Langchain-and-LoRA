# Cấu trúc thư mục

├── .env
├── .gitignore
├── README.md
├── eslint.config.js
├── get_structure.py
├── index.html
├── package.json
├── pnpm-lock.yaml
├── public
│   ├── database.svg
│   └── vite.svg
├── src
│   ├── App.css
│   ├── App.tsx
│   ├── assets
│   │   └── react.svg
│   ├── components
│   │   ├── chat
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatInterface.tsx
│   │   │   └── ChatMessage.tsx
│   │   ├── dashboard
│   │   │   ├── ActivityFeed.tsx
│   │   │   ├── RecentFiles.tsx
│   │   │   └── StatsCards.tsx
│   │   ├── insights
│   │   │   └── DataSummary.tsx
│   │   ├── layout
│   │   │   ├── AuthLayout.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── MainLayout.tsx
│   │   │   ├── MobileMenu.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── ui
│   │   │   ├── alert.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── collapsible.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── loading-screen.tsx
│   │   │   ├── scroll-area.tsx
│   │   │   ├── select.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── textarea.tsx
│   │   │   └── toast.tsx
│   │   ├── upload
│   │   │   └── FileUploader.tsx
│   │   └── visualization
│   │       ├── ChartRenderer.tsx
│   │       ├── ScatterChartRenderer.tsx
│   │       └── Visualizations.tsx
│   ├── contexts
│   │   ├── AuthContext.tsx
│   │   ├── SocketContext.tsx
│   │   └── ThemeContext.tsx
│   ├── hooks
│   │   ├── use-auth.ts
│   │   ├── use-debounce.ts
│   │   ├── use-local-storage.ts
│   │   └── use-toast.ts
│   ├── index.css
│   ├── main.tsx
│   ├── pages
│   │   ├── AnalysisPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── FileDetailPage.tsx
│   │   ├── FilesPage.tsx
│   │   └── auth
│   │       ├── LoginPage.tsx
│   │       └── RegisterPage.tsx
│   ├── services
│   │   └── api.ts
│   ├── types
│   │   ├── common.ts
│   │   └── index.ts
│   ├── utils
│   │   ├── chart.ts
│   │   ├── cn.ts
│   │   ├── data.ts
│   │   ├── format.ts
│   │   └── storage.ts
│   └── vite-env.d.ts
├── structure.md
├── tailwind.config.js
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts