export default function SettingsPage() {
  return (
    <div className="p-3 text-sm">
      <div className="text-neutral-300 mb-2">Settings</div>
      <div className="grid gap-3">
        <a className="text-neutral-300 hover:text-white" href="#">Account</a>
        <a className="text-neutral-300 hover:text-white" href="#">Profile</a>
        <a className="text-neutral-300 hover:text-white" href="#">Project Defaults</a>
        <a className="text-neutral-300 hover:text-white" href="#">API Tokens</a>
      </div>
    </div>
  );
}
