import { Link } from "react-router-dom";
import { LucideIcon } from "lucide-react";

interface FeatureCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  to: string;
}

const FeatureCard = ({
  title,
  description,
  icon: Icon,
  to,
}: FeatureCardProps) => {
  return (
    <Link
      to={to}
      className="group relative overflow-hidden rounded-xl border-[1px] border-slate-200 bg-white p-6 transition-all hover:shadow-lg hover:-translate-y-1"
    >
      <div className="flex items-center gap-4">
        <div className="rounded-lg bg-blue-100 p-3 transition-colors group-hover:bg-blue-200">
          <Icon className="h-6 w-6 text-blue-600" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold leading-none tracking-tight text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>
    </Link>
  );
};

export default FeatureCard;
