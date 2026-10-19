// The Homebrew page (the header's Homebrew item, and the store front row's last card): every app the
// community catalog lists, newest release first, by kind. And an app's own page, which first reads the
// app's file from the catalog (its download and description) and is then a game's page.

import '../assets/Inter-Regular.ttf';
import { Fragment, jsx, jsxs } from 'react/jsx-runtime';
import { useCallback, useEffect, useRef, useState } from 'react';
import { GameScreen } from '../game/index.jsx';
import { SPAN_MAX, fitBytes } from '../i18n/fit.js';
import { useLocale, useT } from '../i18n/index.js';
import { KINDS, detailsOf, loadDetails, refresh, useHomebrew } from '../state/homebrew.js';
import { useNavActions } from '../state/nav.jsx';
import { Button2 } from '../ui/Button.jsx';
import { FocusRing } from '../ui/FocusRing.jsx';
import { DETAILED_CAPTION, GameCard, useFavoriteAction } from '../ui/GameCard.jsx';
import { FocusScope, ScrollView, Text, View, VirtualList, useIsFocused } from '@ps5-react/core';

  var COLUMNS = 6;
  var CARD_WIDTH = 182;
  var CARD_HEIGHT = 243 + DETAILED_CAPTION;
  var TITLE = { fontFamily: "Inter-Regular", fontSize: 30, fontWeight: 600, color: "#f2f2f3", lineHeight: 42, letterSpacing: -0.75 };
  var NOTE = { fontFamily: "Inter-Regular", fontSize: 21, color: "#a3a3ab", lineHeight: 30 };
  var SOURCE = "prosperostore.net";
  // The kind chosen survives opening an app and coming back, which mounts the page again.
  var chosenKind = "all";
  function ChipLabel({ label, count, current }) {
    const focused = useIsFocused();
    return /* @__PURE__ */ (0, jsxs)(Fragment, { children: [
      /* @__PURE__ */ (0, jsx)(FocusRing, {}),
      /* @__PURE__ */ (0, jsx)(Text, { focused, style: [{ fontFamily: "Inter-Regular", fontSize: 21, color: current ? "#0d0d0f" : "#f2f2f3d9", lineHeight: 30 }, focused && !current ? { color: "#f2f2f3" } : null], children: label }),
      /* @__PURE__ */ (0, jsx)(Text, { style: { fontFamily: "Inter-Regular", fontSize: 21, color: current ? "#0d0d0f99" : "#8a8a94", lineHeight: 30 }, children: String(count) })
    ] });
  }
  function Chip({ kind, label, count, current, onPress }) {
    return /* @__PURE__ */ (0, jsx)(View, { focusKey: `homebrew-kind:${kind}`, onPress, style: (state) => [
      { height: 60, flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 14999, paddingHorizontal: 24, backgroundColor: current ? "#f2f2f3" : "#17171a" },
      state.focused && !current ? { backgroundColor: "#2b2b30" } : null
    ], children: /* @__PURE__ */ (0, jsx)(ChipLabel, { label, count, current }) });
  }
  function Grid({ apps }) {
    const { openGame } = useNavActions();
    const renderItem = (0, useCallback)(
      ({ item: app, index }) => /* @__PURE__ */ (0, jsx)(
        GameCard,
        {
          game: app,
          width: CARD_WIDTH,
          detailed: true,
          rowEnd: index % COLUMNS === COLUMNS - 1 || index === apps.length - 1,
          rowStart: index % COLUMNS === 0,
          onPress: () => openGame(app.id, `card:${app.id}`)
        }
      ),
      [apps, openGame]
    );
    return /* @__PURE__ */ (0, jsx)(VirtualList, { style: { marginTop: 36 }, data: apps, numColumns: COLUMNS, itemHeight: CARD_HEIGHT, rowGap: 40, columnGap: 24, initialNumRows: 3, keyExtractor: (app) => app.id, renderItem });
  }
  // Waiting for the list, or why there is none, with a way to ask again.
  function Status({ failed }) {
    const t2 = useT();
    return /* @__PURE__ */ (0, jsxs)(View, { style: { marginTop: 96, alignItems: "center", gap: 30 }, children: [
      /* @__PURE__ */ (0, jsx)(Text, { style: [NOTE, { width: 900, textAlign: "center" }], children: t2(failed ? "homebrew.failed" : "homebrew.loading") }),
      failed ? /* @__PURE__ */ (0, jsx)(Button2, { label: t2("homebrew.retry"), focusKey: "homebrew:retry", autoFocus: true, onPress: () => void refresh(true) }) : null
    ] });
  }
  function HomebrewScreen({ onBack }) {
    const t2 = useT();
    const { rtl } = useLocale();
    const { apps, status } = useHomebrew();
    const [kind, setKind] = (0, useState)(chosenKind);
    const choose = (next) => {
      chosenKind = next;
      setKind(next);
    };
    // On a first launch the list can arrive after the page opened, with nothing focused yet.
    const { focusLater } = useNavActions();
    const listed = apps.length > 0;
    const listedAtOpen = (0, useRef)(listed);
    (0, useEffect)(() => {
      if (listed && !listedAtOpen.current) focusLater(`homebrew-kind:${chosenKind}`);
    }, [listed]);
    const counts = Object.fromEntries(KINDS.map((name) => [name, apps.filter((app) => app.homebrew.kind === name).length]));
    const shown = kind === "all" ? apps : apps.filter((app) => app.homebrew.kind === kind);
    const onAction = useFavoriteAction();
    const back2 = () => {
      onBack();
      return true;
    };
    // Not a trap: Up from the kinds reaches the header, as on Downloads and Files.
    return /* @__PURE__ */ (0, jsx)(FocusScope, { autoFocus: true, onBack: back2, onAction, children: /* @__PURE__ */ (0, jsxs)(ScrollView, { style: { flex: 1, paddingHorizontal: 48, paddingTop: 48, paddingBottom: 96 }, children: [
      /* @__PURE__ */ (0, jsxs)(View, { scrollAnchor: true, children: [
        /* @__PURE__ */ (0, jsxs)(Text, { style: TITLE, children: [
          fitBytes(t2("nav.homebrew"), SPAN_MAX),
          apps.length ? /* @__PURE__ */ (0, jsx)(Text, { style: { fontWeight: 400, color: "#8a8a94" }, children: fitBytes(`  ${t2("homebrew.count", { count: apps.length })}`, SPAN_MAX) }) : null
        ] }),
        /* @__PURE__ */ (0, jsx)(Text, { style: [NOTE, { marginTop: 12, width: 1400, textAlign: rtl ? "right" : "left" }], children: t2("homebrew.about", { source: SOURCE }) }),
        apps.length ? /* @__PURE__ */ (0, jsx)(FocusScope, { row: true, children: /* @__PURE__ */ (0, jsx)(View, { style: { marginTop: 36, flexDirection: "row", flexWrap: "wrap", gap: 12 }, children: ["all", ...KINDS].filter((name) => name === "all" || counts[name] > 0).map(
          (name) => /* @__PURE__ */ (0, jsx)(Chip, { kind: name, label: t2(`homebrew.kind.${name}`), count: name === "all" ? apps.length : counts[name], current: kind === name, onPress: () => choose(name) }, name)
        ) }) }) : null
      ] }),
      apps.length ? /* @__PURE__ */ (0, jsx)(Grid, { apps: shown }, kind) : /* @__PURE__ */ (0, jsx)(Status, { failed: status === "failed" })
    ] }) });
  }
  // An app's page: its file is read first, so the page opens with its download ready.
  function HomebrewGame({ game, ...props }) {
    const t2 = useT();
    const [state, setState] = (0, useState)(() => !game ? "failed" : detailsOf(game) ? "ready" : "loading");
    const [attempt, setAttempt] = (0, useState)(0);
    (0, useEffect)(() => {
      if (!game || state === "ready") return void 0;
      let live = true;
      setState("loading");
      loadDetails(game).then(() => live && setState("ready"), (error2) => {
        console.log(`[homebrew] ${game.id} not read: ${error2.message}`);
        if (live) setState("failed");
      });
      return () => {
        live = false;
      };
    }, [game?.id, attempt]);
    if (state === "ready") return /* @__PURE__ */ (0, jsx)(GameScreen, { game, ...props });
    const back2 = () => {
      props.onBack();
      return true;
    };
    return /* @__PURE__ */ (0, jsx)(FocusScope, { trap: true, autoFocus: true, onBack: back2, children: /* @__PURE__ */ (0, jsxs)(View, { style: { flex: 1, alignItems: "center", justifyContent: "center", gap: 30 }, children: [
      game ? /* @__PURE__ */ (0, jsx)(Text, { style: TITLE, children: game.title }) : null,
      /* @__PURE__ */ (0, jsx)(Text, { style: [NOTE, { width: 900, textAlign: "center" }], children: t2(state === "failed" ? "homebrew.appFailed" : "homebrew.loadingApp") }),
      /* @__PURE__ */ (0, jsxs)(View, { style: { flexDirection: "row", gap: 15 }, children: [
        state === "failed" && game ? /* @__PURE__ */ (0, jsx)(Button2, { label: t2("homebrew.retry"), focusKey: "homebrew-app:retry", onPress: () => setAttempt((count) => count + 1) }) : null,
        /* @__PURE__ */ (0, jsx)(Button2, { variant: "outline", label: t2("hints.back"), focusKey: "homebrew-app:back", onPress: props.onBack })
      ] })
    ] }) });
  }

export { HomebrewGame, HomebrewScreen };
