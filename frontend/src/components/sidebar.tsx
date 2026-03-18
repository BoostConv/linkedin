"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/posts", label: "Posts", icon: "📝" },
  { href: "/ideas", label: "Boîte à idées", icon: "💡" },
  { href: "/calendar", label: "Calendrier", icon: "📅" },
  { href: "/carousel", label: "Carrousels", icon: "🎠" },
  { href: "/comments", label: "Commentaires", icon: "💬" },
  { href: "/competitors", label: "Veille", icon: "🔍" },
  { href: "/analytics", label: "Analytics", icon: "📈" },
  { href: "/products", label: "Produits", icon: "📦" },
  { href: "/settings", label: "Réglages", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">LinkedIn Auto</h1>
        <p className="text-sm text-gray-500 mt-1">Boost Conversion</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
            ST
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">Sébastien</p>
            <p className="text-xs text-gray-500">Boost Conversion</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
