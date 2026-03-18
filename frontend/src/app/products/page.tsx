"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api, Product } from "@/lib/api";

function ProductForm({
  product,
  onSave,
  onCancel,
}: {
  product?: Product;
  onSave: (data: Partial<Product>) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(product?.name || "");
  const [slug, setSlug] = useState(product?.slug || "");
  const [tagline, setTagline] = useState(product?.tagline || "");
  const [description, setDescription] = useState(product?.description || "");
  const [targetAudience, setTargetAudience] = useState(product?.target_audience || "");
  const [benefits, setBenefits] = useState((product?.key_benefits || []).join("\n"));
  const [painPoints, setPainPoints] = useState((product?.pain_points || []).join("\n"));
  const [proofPoints, setProofPoints] = useState((product?.proof_points || []).join("\n"));
  const [ctaText, setCtaText] = useState(product?.cta_text || "");
  const [priceInfo, setPriceInfo] = useState(product?.price_info || "");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await onSave({
        name,
        slug: slug || name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
        tagline,
        description,
        target_audience: targetAudience,
        key_benefits: benefits.split("\n").filter(Boolean),
        pain_points: painPoints.split("\n").filter(Boolean),
        proof_points: proofPoints ? proofPoints.split("\n").filter(Boolean) : [],
        cta_text: ctaText || null,
        price_info: priceInfo || null,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Nom du produit</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="NeuroCRO Score" />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Slug</label>
          <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="neurocro-score" />
        </div>
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700 block mb-1">Tagline (une phrase)</label>
        <Input value={tagline} onChange={(e) => setTagline(e.target.value)} placeholder="Diagnostic complet en 5 minutes" />
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700 block mb-1">Description (pour le contexte IA)</label>
        <Textarea value={description} onChange={(e) => setDescription(e.target.value)} className="min-h-[80px]" placeholder="Description complète du produit..." />
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700 block mb-1">Audience cible</label>
        <Textarea value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)} className="min-h-[60px]" placeholder="Qui est ce produit pour ?" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Bénéfices clés (1 par ligne)</label>
          <Textarea value={benefits} onChange={(e) => setBenefits(e.target.value)} className="min-h-[80px]" placeholder="Diagnostic en 5 minutes&#10;Score objectif&#10;Roadmap priorisée" />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Pain points résolus (1 par ligne)</label>
          <Textarea value={painPoints} onChange={(e) => setPainPoints(e.target.value)} className="min-h-[80px]" placeholder="Mon CR stagne&#10;Le ROI baisse&#10;Pas de priorités" />
        </div>
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700 block mb-1">Preuves / Stats (1 par ligne)</label>
        <Textarea value={proofPoints} onChange={(e) => setProofPoints(e.target.value)} className="min-h-[60px]" placeholder="200+ marques diagnostiquées&#10;CR x2 en moyenne" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">CTA par défaut</label>
          <Input value={ctaText} onChange={(e) => setCtaText(e.target.value)} placeholder="DM moi 'NEUROCRO' pour..." />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-1">Info prix (optionnel)</label>
          <Input value={priceInfo} onChange={(e) => setPriceInfo(e.target.value)} placeholder="Gratuit / 500€ / Sur devis" />
        </div>
      </div>
      <div className="flex gap-2 pt-2">
        <Button onClick={handleSubmit} disabled={saving || !name.trim()}>
          {saving ? "Sauvegarde..." : product ? "Mettre à jour" : "Créer le produit"}
        </Button>
        <Button variant="outline" onClick={onCancel}>Annuler</Button>
      </div>
    </div>
  );
}

function ProductCard({
  product,
  onEdit,
  onDelete,
}: {
  product: Product;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900">{product.name}</h3>
              <Badge variant="outline" className="text-xs">{product.slug}</Badge>
              {!product.is_active && <Badge className="bg-gray-100 text-gray-500">Inactif</Badge>}
            </div>
            <p className="text-sm text-blue-600 mb-2">{product.tagline}</p>
            <p className="text-sm text-gray-600 line-clamp-2">{product.description}</p>

            <div className="mt-3 flex gap-4 flex-wrap">
              {product.key_benefits.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-700">Bénéfices</p>
                  <div className="flex gap-1 flex-wrap mt-0.5">
                    {product.key_benefits.slice(0, 3).map((b, i) => (
                      <Badge key={i} className="bg-green-50 text-green-700 text-xs">{b}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {product.pain_points.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-700">Pain points</p>
                  <div className="flex gap-1 flex-wrap mt-0.5">
                    {product.pain_points.slice(0, 3).map((p, i) => (
                      <Badge key={i} className="bg-red-50 text-red-700 text-xs">{p}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {product.cta_text && (
              <p className="text-xs text-gray-500 mt-2">CTA: <span className="text-blue-600">{product.cta_text}</span></p>
            )}
          </div>
          <div className="flex flex-col gap-1.5 shrink-0">
            <Button variant="outline" size="sm" onClick={onEdit}>Éditer</Button>
            <Button variant="outline" size="sm" className="text-red-500" onClick={onDelete}>Supprimer</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  const loadProducts = () => {
    setLoading(true);
    api.listProducts().then(setProducts).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadProducts(); }, []);

  const handleCreate = async (data: Partial<Product>) => {
    await api.createProduct(data);
    setCreating(false);
    loadProducts();
  };

  const handleUpdate = async (data: Partial<Product>) => {
    if (!editingProduct) return;
    await api.updateProduct(editingProduct.id, data);
    setEditingProduct(null);
    loadProducts();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer ce produit ?")) return;
    await api.deleteProduct(id);
    loadProducts();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Produits & Services</h1>
          <p className="text-sm text-gray-500 mt-1">
            L&apos;IA utilise ces produits pour générer des posts qui font la promotion de vos offres.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>Ajouter un produit</Button>
      </div>

      {(creating || editingProduct) && (
        <Card>
          <CardContent className="p-4">
            <h3 className="font-medium mb-3">{editingProduct ? "Modifier le produit" : "Nouveau produit"}</h3>
            <ProductForm
              product={editingProduct || undefined}
              onSave={editingProduct ? handleUpdate : handleCreate}
              onCancel={() => { setCreating(false); setEditingProduct(null); }}
            />
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="text-sm text-gray-500 text-center py-8">Chargement...</p>
      ) : products.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-gray-500 text-center py-8">
              Aucun produit configuré. Ajoutez vos offres pour que l&apos;IA les intègre dans la génération de contenu.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onEdit={() => setEditingProduct(product)}
              onDelete={() => handleDelete(product.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
