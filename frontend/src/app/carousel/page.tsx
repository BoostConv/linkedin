"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, CarouselSlide, Pillar } from "@/lib/api";
import { useEffect } from "react";

const EMPTY_SLIDE: CarouselSlide = {
  slide_type: "content",
  title: "",
  body: "",
  stat_number: "",
  stat_label: "",
  subtitle: "",
};

export default function CarouselPage() {
  const [pillars, setPillars] = useState<Pillar[]>([]);
  const [topic, setTopic] = useState("");
  const [selectedPillar, setSelectedPillar] = useState("");
  const [numSlides, setNumSlides] = useState(8);
  const [slides, setSlides] = useState<CarouselSlide[]>([]);
  const [generating, setGenerating] = useState(false);
  const [pdfPreview, setPdfPreview] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedPostId, setSavedPostId] = useState<string | null>(null);
  const [activeSlide, setActiveSlide] = useState(0);

  useEffect(() => {
    api.listPillars().then(setPillars).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    if (!topic.trim() || !selectedPillar) return;
    setGenerating(true);
    setPdfPreview(null);
    setSavedPostId(null);
    try {
      const pillarName =
        pillars.find((p) => p.id === selectedPillar)?.name || "";
      const result = await api.generateCarouselSlides({
        topic,
        pillar_name: pillarName,
        num_slides: numSlides,
      });
      setSlides(result.slides);
      setActiveSlide(0);
    } catch (e) {
      alert("Erreur lors de la génération des slides.");
    } finally {
      setGenerating(false);
    }
  };

  const handlePreview = async () => {
    if (slides.length === 0) return;
    setSaving(true);
    try {
      const result = await api.generateCarouselPDF({ slides });
      setPdfPreview(result.pdf_base64);
    } catch {
      alert("Erreur lors de la génération du PDF.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAsDraft = async () => {
    if (slides.length === 0) return;
    setSaving(true);
    try {
      const result = await api.generateCarouselPDF({
        slides,
        save_as_draft: true,
        pillar_id: selectedPillar || undefined,
      });
      setSavedPostId(result.post_id);
      setPdfPreview(result.pdf_base64);
    } catch {
      alert("Erreur lors de la sauvegarde.");
    } finally {
      setSaving(false);
    }
  };

  const updateSlide = (index: number, updates: Partial<CarouselSlide>) => {
    setSlides((prev) =>
      prev.map((s, i) => (i === index ? { ...s, ...updates } : s))
    );
  };

  const addSlide = () => {
    setSlides((prev) => [...prev, { ...EMPTY_SLIDE }]);
    setActiveSlide(slides.length);
  };

  const removeSlide = (index: number) => {
    if (slides.length <= 2) return;
    setSlides((prev) => prev.filter((_, i) => i !== index));
    if (activeSlide >= slides.length - 1) setActiveSlide(Math.max(0, slides.length - 2));
  };

  const slideTypeColors: Record<string, string> = {
    title: "bg-blue-100 text-blue-700",
    content: "bg-gray-100 text-gray-700",
    stat: "bg-purple-100 text-purple-700",
    cta: "bg-green-100 text-green-700",
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">
        Générateur de carrousels
      </h1>

      {/* Generation form */}
      <Card>
        <CardHeader>
          <CardTitle>Nouveau carrousel</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sujet du carrousel
              </label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Ex: 5 erreurs sur vos landing pages..."
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Pilier
              </label>
              <select
                value={selectedPillar}
                onChange={(e) => setSelectedPillar(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value="">Choisir...</option>
                {pillars.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre de slides
              </label>
              <input
                type="number"
                min={4}
                max={15}
                value={numSlides}
                onChange={(e) => setNumSlides(Number(e.target.value))}
                className="w-20 px-3 py-2 border border-gray-200 rounded-lg text-sm"
              />
            </div>
            <div className="pt-5">
              <button
                onClick={handleGenerate}
                disabled={generating || !topic.trim() || !selectedPillar}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {generating ? "Génération en cours..." : "Générer les slides"}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Slide editor */}
      {slides.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Slide list */}
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">
                Slides ({slides.length})
              </h3>
              <button
                onClick={addSlide}
                className="text-xs text-blue-600 hover:underline"
              >
                + Ajouter
              </button>
            </div>
            {slides.map((slide, i) => (
              <button
                key={i}
                onClick={() => setActiveSlide(i)}
                className={`w-full text-left px-3 py-2.5 rounded-lg border text-sm transition-colors ${
                  activeSlide === i
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs text-gray-400 shrink-0">
                      {i + 1}.
                    </span>
                    <Badge
                      className={`text-xs shrink-0 ${
                        slideTypeColors[slide.slide_type] || "bg-gray-100"
                      }`}
                    >
                      {slide.slide_type}
                    </Badge>
                    <span className="truncate text-gray-700">
                      {slide.title || "(sans titre)"}
                    </span>
                  </div>
                  {slides.length > 2 && (
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        removeSlide(i);
                      }}
                      className="text-red-400 hover:text-red-600 cursor-pointer text-xs shrink-0 ml-1"
                    >
                      x
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>

          {/* Active slide editor */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Slide {activeSlide + 1}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type
                  </label>
                  <select
                    value={slides[activeSlide]?.slide_type || "content"}
                    onChange={(e) =>
                      updateSlide(activeSlide, { slide_type: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  >
                    <option value="title">Titre (slide d&apos;ouverture)</option>
                    <option value="content">Contenu</option>
                    <option value="stat">Statistique</option>
                    <option value="cta">CTA (slide de fin)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Titre
                  </label>
                  <input
                    type="text"
                    value={slides[activeSlide]?.title || ""}
                    onChange={(e) =>
                      updateSlide(activeSlide, { title: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  />
                </div>

                {(slides[activeSlide]?.slide_type === "content" ||
                  slides[activeSlide]?.slide_type === "cta") && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Corps du texte
                    </label>
                    <textarea
                      value={slides[activeSlide]?.body || ""}
                      onChange={(e) =>
                        updateSlide(activeSlide, { body: e.target.value })
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                    />
                  </div>
                )}

                {slides[activeSlide]?.slide_type === "stat" && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Chiffre clé
                      </label>
                      <input
                        type="text"
                        value={slides[activeSlide]?.stat_number || ""}
                        onChange={(e) =>
                          updateSlide(activeSlide, {
                            stat_number: e.target.value,
                          })
                        }
                        placeholder="Ex: 97%, +340%, 3x"
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Label du chiffre
                      </label>
                      <input
                        type="text"
                        value={slides[activeSlide]?.stat_label || ""}
                        onChange={(e) =>
                          updateSlide(activeSlide, {
                            stat_label: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      />
                    </div>
                  </>
                )}

                {(slides[activeSlide]?.slide_type === "title" ||
                  slides[activeSlide]?.slide_type === "cta") && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {slides[activeSlide]?.slide_type === "title"
                        ? "Sous-titre"
                        : "Texte du bouton CTA"}
                    </label>
                    <input
                      type="text"
                      value={slides[activeSlide]?.subtitle || ""}
                      onChange={(e) =>
                        updateSlide(activeSlide, { subtitle: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                    />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="flex gap-3 mt-4">
              <button
                onClick={handlePreview}
                disabled={saving}
                className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
              >
                {saving ? "..." : "Prévisualiser le PDF"}
              </button>
              <button
                onClick={handleSaveAsDraft}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Sauvegarde..." : "Sauvegarder en brouillon"}
              </button>
              {savedPostId && (
                <span className="flex items-center text-sm text-green-600">
                  Sauvegardé !
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* PDF Preview */}
      {pdfPreview && (
        <Card>
          <CardHeader>
            <CardTitle>Apercu du PDF</CardTitle>
          </CardHeader>
          <CardContent>
            <iframe
              src={`data:application/pdf;base64,${pdfPreview}`}
              className="w-full h-[600px] border border-gray-200 rounded-lg"
              title="Carousel PDF Preview"
            />
            <div className="mt-3">
              <a
                href={`data:application/pdf;base64,${pdfPreview}`}
                download="carousel.pdf"
                className="text-sm text-blue-600 hover:underline"
              >
                Télécharger le PDF
              </a>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
