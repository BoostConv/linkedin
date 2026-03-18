"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api, BrandConfig } from "@/lib/api";

function ColorInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-8 h-8 rounded-md border border-gray-200 shrink-0 cursor-pointer"
        style={{ backgroundColor: value }}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "color";
          input.value = value;
          input.onchange = (e) => onChange((e.target as HTMLInputElement).value);
          input.click();
        }}
      />
      <div className="flex-1">
        <label className="text-xs font-medium text-gray-600 block">{label}</label>
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-7 text-xs font-mono"
        />
      </div>
    </div>
  );
}

function BrandingSection() {
  const [brand, setBrand] = useState<BrandConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getBrandConfig().then((c) => { setBrand(c); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!brand) return;
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.updateBrandConfig(brand);
      setBrand(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("Réinitialiser la charte graphique aux valeurs par défaut ?")) return;
    const defaults = await api.resetBrandConfig();
    setBrand(defaults);
  };

  if (loading || !brand) return null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Charte graphique</CardTitle>
          {saved && <Badge className="bg-green-100 text-green-700">Sauvegardé</Badge>}
        </div>
        <p className="text-sm text-gray-500">
          Ces couleurs et polices sont utilisées pour générer les carrousels et visuels.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Color preview */}
        <div className="flex gap-1.5 h-10 rounded-lg overflow-hidden border">
          {[brand.primary_color, brand.secondary_color, brand.text_color, brand.light_text_color, brand.accent_bg_color, brand.highlight_color, brand.bg_color].map((c, i) => (
            <div key={i} className="flex-1" style={{ backgroundColor: c }} />
          ))}
        </div>

        {/* Colors grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <ColorInput label="Couleur principale" value={brand.primary_color} onChange={(v) => setBrand({ ...brand, primary_color: v })} />
          <ColorInput label="Couleur secondaire" value={brand.secondary_color} onChange={(v) => setBrand({ ...brand, secondary_color: v })} />
          <ColorInput label="Fond" value={brand.bg_color} onChange={(v) => setBrand({ ...brand, bg_color: v })} />
          <ColorInput label="Texte principal" value={brand.text_color} onChange={(v) => setBrand({ ...brand, text_color: v })} />
          <ColorInput label="Texte clair" value={brand.light_text_color} onChange={(v) => setBrand({ ...brand, light_text_color: v })} />
          <ColorInput label="Fond accent" value={brand.accent_bg_color} onChange={(v) => setBrand({ ...brand, accent_bg_color: v })} />
          <ColorInput label="Highlight" value={brand.highlight_color} onChange={(v) => setBrand({ ...brand, highlight_color: v })} />
        </div>

        {/* Typography & Author */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Police titres</label>
            <Input value={brand.font_titles} onChange={(e) => setBrand({ ...brand, font_titles: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Police corps</label>
            <Input value={brand.font_body} onChange={(e) => setBrand({ ...brand, font_body: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Nom auteur</label>
            <Input value={brand.author_name} onChange={(e) => setBrand({ ...brand, author_name: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Titre auteur</label>
            <Input value={brand.author_title} onChange={(e) => setBrand({ ...brand, author_title: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Texte logo</label>
            <Input value={brand.logo_text} onChange={(e) => setBrand({ ...brand, logo_text: e.target.value })} />
          </div>
        </div>

        <div className="flex gap-3">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Sauvegarde..." : "Sauvegarder la charte"}
          </Button>
          <Button variant="outline" onClick={handleReset}>Réinitialiser</Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  // Email config
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [currentEmail, setCurrentEmail] = useState<string | null>(null);
  const [currentHost, setCurrentHost] = useState<string | null>(null);
  const [imapHost, setImapHost] = useState("imap.gmail.com");
  const [imapPort, setImapPort] = useState(993);
  const [emailAddress, setEmailAddress] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{ ok: boolean; message: string } | null>(null);

  // Poll
  const [polling, setPolling] = useState(false);
  const [pollResult, setPollResult] = useState<{
    processed: number;
    errors: number;
    details: string[];
  } | null>(null);

  useEffect(() => {
    api.getEmailConfig().then((config) => {
      setEmailConfigured(config.configured);
      setCurrentEmail(config.email_address);
      setCurrentHost(config.imap_host);
      if (config.email_address) setEmailAddress(config.email_address);
      if (config.imap_host) setImapHost(config.imap_host);
    }).catch(console.error);
  }, []);

  const handleSaveEmail = async () => {
    setSaving(true);
    setSaveResult(null);
    try {
      const result = await api.updateEmailConfig({
        imap_host: imapHost,
        imap_port: imapPort,
        email_address: emailAddress,
        email_password: emailPassword,
      });
      setSaveResult({ ok: true, message: result.message });
      setEmailConfigured(true);
      setCurrentEmail(emailAddress);
      setCurrentHost(imapHost);
    } catch (err) {
      setSaveResult({
        ok: false,
        message: err instanceof Error ? err.message : "Erreur de connexion",
      });
    } finally {
      setSaving(false);
    }
  };

  const handlePoll = async () => {
    setPolling(true);
    setPollResult(null);
    try {
      const result = await api.pollEmails();
      setPollResult(result);
    } catch (err) {
      setPollResult({
        processed: 0,
        errors: 1,
        details: [err instanceof Error ? err.message : "Erreur"],
      });
    } finally {
      setPolling(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Paramètres</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configuration de l&apos;outil.
        </p>
      </div>

      {/* Email Inbox */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Inbox email</CardTitle>
            {emailConfigured ? (
              <Badge className="bg-green-100 text-green-700">Connecté</Badge>
            ) : (
              <Badge className="bg-gray-100 text-gray-500">Non configuré</Badge>
            )}
          </div>
          <p className="text-sm text-gray-500">
            Configurez une adresse email dédiée pour envoyer vos idées par mail.
            Chaque email reçu sera transformé en idée dans votre boîte à idées.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {emailConfigured && currentEmail && (
            <div className="bg-green-50 rounded-lg px-4 py-3 text-sm text-green-700">
              Connecté à <strong>{currentEmail}</strong> via {currentHost}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">
                Serveur IMAP
              </label>
              <Input
                placeholder="imap.gmail.com"
                value={imapHost}
                onChange={(e) => setImapHost(e.target.value)}
              />
              <p className="text-xs text-gray-400 mt-1">
                Gmail: imap.gmail.com | Outlook: outlook.office365.com
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">
                Port IMAP
              </label>
              <Input
                type="number"
                value={imapPort}
                onChange={(e) => setImapPort(Number(e.target.value))}
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Adresse email
            </label>
            <Input
              type="email"
              placeholder="mes-idees-linkedin@gmail.com"
              value={emailAddress}
              onChange={(e) => setEmailAddress(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Mot de passe d&apos;application
            </label>
            <Input
              type="password"
              placeholder="xxxx xxxx xxxx xxxx"
              value={emailPassword}
              onChange={(e) => setEmailPassword(e.target.value)}
            />
            <p className="text-xs text-gray-400 mt-1">
              Pour Gmail : utilisez un{" "}
              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 underline"
              >
                mot de passe d&apos;application
              </a>
              {" "}(pas votre mot de passe Gmail). Activez d&apos;abord la validation en 2 étapes.
            </p>
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleSaveEmail}
              disabled={!imapHost || !emailAddress || !emailPassword || saving}
            >
              {saving ? "Test de connexion..." : "Tester et sauvegarder"}
            </Button>

            {emailConfigured && (
              <Button variant="outline" onClick={handlePoll} disabled={polling}>
                {polling ? "Vérification..." : "Vérifier les emails maintenant"}
              </Button>
            )}
          </div>

          {saveResult && (
            <div
              className={`rounded-lg px-4 py-3 text-sm ${
                saveResult.ok
                  ? "bg-green-50 text-green-700"
                  : "bg-red-50 text-red-700"
              }`}
            >
              {saveResult.message}
            </div>
          )}

          {pollResult && (
            <div className="rounded-lg border px-4 py-3 space-y-2">
              <div className="flex items-center gap-3">
                <Badge className={pollResult.processed > 0 ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}>
                  {pollResult.processed} idée(s) importée(s)
                </Badge>
                {pollResult.errors > 0 && (
                  <Badge className="bg-red-100 text-red-700">
                    {pollResult.errors} erreur(s)
                  </Badge>
                )}
              </div>
              {pollResult.details.length > 0 && (
                <ul className="text-xs text-gray-500 space-y-1">
                  {pollResult.details.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* How-to guide */}
          <div className="border-t pt-4 mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Comment ça marche ?</h4>
            <ol className="text-sm text-gray-500 space-y-1 list-decimal list-inside">
              <li>Créez un compte Gmail dédié (ex: <code className="bg-gray-100 px-1 rounded">mes-idees-linkedin@gmail.com</code>)</li>
              <li>Activez la validation en 2 étapes sur ce compte</li>
              <li>Générez un <strong>mot de passe d&apos;application</strong> dans les paramètres Google</li>
              <li>Configurez l&apos;adresse ci-dessus</li>
              <li>Quand vous voyez un article/post intéressant, transférez-le par email à cette adresse</li>
              <li>L&apos;outil récupère automatiquement les emails et les transforme en idées</li>
            </ol>
          </div>
        </CardContent>
      </Card>

      {/* Charte graphique */}
      <BrandingSection />

      {/* LinkedIn connection status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">LinkedIn</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            La connexion LinkedIn permet de publier automatiquement vos posts et de récupérer les analytics.
          </p>
          <Button variant="outline" className="mt-3" onClick={async () => {
            try {
              const result = await api.me() as { linkedin_person_id?: string };
              if (result.linkedin_person_id) {
                alert("LinkedIn est connecté.");
              } else {
                const authResult = await fetch("http://localhost:8000/api/auth/linkedin/authorize");
                const data = await authResult.json();
                window.open(data.authorization_url, "_blank");
              }
            } catch {
              alert("Erreur de vérification");
            }
          }}>
            Vérifier la connexion LinkedIn
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
