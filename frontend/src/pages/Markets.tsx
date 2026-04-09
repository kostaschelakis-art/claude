import MarketConfig from '@/components/Markets/MarketConfig';

export default function Markets() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Market Management</h1>
        <p className="text-gray-400 text-sm mt-1">Configure market-specific legal requirements, branding overrides, and data partitioning.</p>
      </div>
      <MarketConfig />
    </div>
  );
}
