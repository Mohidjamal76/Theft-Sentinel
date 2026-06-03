import { BuildingOfficeIcon, MapPinIcon, UserCircleIcon } from '@heroicons/react/24/outline';

const TenantContextBanner = ({ user }) => {
  if (!user || user.role === 'SUPER_ADMIN' || !user.company_name) {
    return null;
  }

  const items = [
    { label: 'Company', value: user.company_name, icon: BuildingOfficeIcon },
    { label: 'Branch', value: user.branch_name, icon: MapPinIcon },
    { label: 'Branch Admin', value: user.branch_admin_name, icon: UserCircleIcon },
  ].filter((item) => item.value);

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mb-6 glass rounded-xl border border-ai-blue/20 px-4 py-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-lg bg-ai-blue/10 border border-ai-blue/20 flex items-center justify-center flex-shrink-0">
                <Icon className="h-5 w-5 text-ai-blue" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-wider text-dark-text-muted">{item.label}</p>
                <p className="text-sm font-semibold text-white truncate">{item.value}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TenantContextBanner;
