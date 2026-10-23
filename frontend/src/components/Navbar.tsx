import React from 'react';
import { ShieldCheck, Car, RefreshCw, CheckCircle2 } from 'lucide-react';

interface NavbarProps {
  currentTab: 'home' | 'inspect' | 'handover' | 'verify';
  onSelectTab: (tab: 'home' | 'inspect' | 'handover' | 'verify') => void;
  onOpenCreateModal: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onSelectTab, onOpenCreateModal }) => {
  return (
    <header className="sticky top-0 z-50 bg-black/90 backdrop-blur-md border-b border-neutral-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div 
          className="flex items-center space-x-3 cursor-pointer group"
          onClick={() => onSelectTab('home')}
        >
          <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center font-black text-white text-base shadow-lg shadow-orange-600/30">
            C
          </div>
          <span className="font-extrabold tracking-wider text-sm sm:text-base text-white group-hover:text-orange-400 transition-colors uppercase">
            CarCheck Agent
          </span>
          <span className="hidden sm:inline-block text-[11px] font-mono px-2 py-0.5 rounded-full bg-neutral-800 text-neutral-400 border border-neutral-700">
            v1.1
          </span>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 sm:space-x-2">
          <button
            onClick={() => onSelectTab('home')}
            className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all ${
              currentTab === 'home'
                ? 'bg-neutral-800 text-white shadow'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
            }`}
          >
            HOME
          </button>
          <button
            onClick={() => {
              onSelectTab('inspect');
              onOpenCreateModal();
            }}
            className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all ${
              currentTab === 'inspect'
                ? 'bg-orange-600 text-white shadow-lg shadow-orange-600/30'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
            }`}
          >
            INSPECT
          </button>
          <button
            onClick={() => onSelectTab('handover')}
            className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all ${
              currentTab === 'handover'
                ? 'bg-neutral-800 text-white shadow'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
            }`}
          >
            HANDOVER
          </button>
          <button
            onClick={() => onSelectTab('verify')}
            className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all ${
              currentTab === 'verify'
                ? 'bg-neutral-800 text-white shadow'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
            }`}
          >
            VERIFY
          </button>
        </nav>

        {/* Demo Status */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/80 text-emerald-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="hidden md:inline">Trust Layer Active</span>
            <span className="md:hidden">Active</span>
          </div>
        </div>
      </div>
    </header>
  );
};
