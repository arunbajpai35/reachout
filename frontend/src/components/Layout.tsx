import { Link, NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Send } from "lucide-react";

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Send className="h-4 w-4 text-indigo-600" />
            ReachOut
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <NavItem to="/">Workspace</NavItem>
            <NavItem to="/candidate">Profile</NavItem>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cn(
          "rounded-md px-3 py-1.5 transition-colors",
          isActive ? "bg-slate-100 text-slate-900" : "text-slate-500 hover:text-slate-900",
        )
      }
    >
      {children}
    </NavLink>
  );
}
