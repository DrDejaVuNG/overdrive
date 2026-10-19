// The store front's Homebrew row, under "You might like": the forty apps released last, then a card
// that opens the Homebrew page with the rest. It shows once the catalog's list has been read (kept on
// disk after the first launch), and not at all while there is none.

import '../assets/Inter-Regular.ttf';
import { Fragment, jsx, jsxs } from 'react/jsx-runtime';
import { memo, useState } from 'react';
import { ART_AHEAD, FIRST_ART, GameRail } from './GameRail.jsx';
import { focusEnd, useLocale, useT } from '../i18n/index.js';
import { useHomebrew } from '../state/homebrew.js';
import { useNavActions } from '../state/nav.jsx';
import { FocusFrame } from '../ui/FocusRing.jsx';
import { DETAILED_CAPTION, GameCard } from '../ui/GameCard.jsx';
import { Icon } from '../ui/Icon.jsx';
import { colors } from '../ui/colors.js';
import { EASE_OUT } from '../ui/ease.js';
import { px } from '../ui/scale.js';
import { Image, Text, View, motion, useIsFocused } from '@ps5-react/core';

  var WIDTH = 152;
  var SHOWN = 40;
  var MORE_KEY = "homebrew:more";
  var TILE = { width: px(WIDTH), height: px(Math.round(WIDTH * 4 / 3)), borderRadius: px(8) };
  var CAPTION = { width: px(WIDTH), height: px(DETAILED_CAPTION) };
  // Four icons in a square, as the card's picture.
  var GAP = 9;
  var ICON = Math.floor((WIDTH - 24 - GAP) / 2);
  var MOSAIC = { width: px(ICON * 2 + GAP), flexDirection: "row", flexWrap: "wrap", gap: px(GAP) };
  var ICON_BOX = { width: px(ICON), height: px(ICON), borderRadius: px(9), backgroundColor: "#212125" };
  var lift = { type: "tween", duration: 0.3, ease: EASE_OUT };
  function MoreCard({ apps, count }) {
    const t2 = useT();
    const focused = useIsFocused();
    return /* @__PURE__ */ (0, jsxs)(Fragment, { children: [
      /* @__PURE__ */ (0, jsxs)(motion.View, { style: [{ position: "relative", alignItems: "center", justifyContent: "center", backgroundColor: "#17171a" }, TILE], initial: false, animate: { y: focused ? -6 : 0 }, transition: lift, children: [
        /* @__PURE__ */ (0, jsx)(View, { style: MOSAIC, children: apps.map(
          (app) => app.art.cover ? /* @__PURE__ */ (0, jsx)(Image, { source: { uri: app.art.cover }, resizeMode: "cover", style: ICON_BOX }, app.id) : /* @__PURE__ */ (0, jsx)(View, { style: ICON_BOX }, app.id)
        ) }),
        /* @__PURE__ */ (0, jsx)(FocusFrame, { round: "lg" })
      ] }),
      /* @__PURE__ */ (0, jsxs)(View, { style: [{ paddingTop: 15 }, CAPTION], children: [
        /* @__PURE__ */ (0, jsx)(Text, { style: { fontFamily: "Inter-Regular", fontSize: 20, color: "#8a8a94", lineHeight: 24 }, children: t2("homebrew.count", { count }) }),
        /* @__PURE__ */ (0, jsx)(Text, { focused, style: [{ marginTop: 6, fontFamily: "Inter-Regular", fontSize: 23, fontWeight: 600, color: "#f2f2f3e6", lineHeight: 30, numberOfLines: 1, ellipsizeMode: "tail" }, focused ? { color: "#f2f2f3" } : null], children: t2("nav.homebrew") }),
        /* @__PURE__ */ (0, jsxs)(View, { style: { marginTop: 9, flexDirection: "row", alignItems: "center", gap: 6 }, children: [
          /* @__PURE__ */ (0, jsx)(Text, { focused, style: [{ fontFamily: "Inter-Regular", fontSize: 20, color: "#a3a3ab" }, focused ? { color: "#f2f2f3" } : null], children: t2("common.seeAll") }),
          /* @__PURE__ */ (0, jsx)(Icon, { name: "chevronRight", size: 14, color: focused ? colors.fg : colors.muted })
        ] })
      ] })
    ] });
  }
  var HomebrewRail = (0, memo)(function HomebrewRail2() {
    const t2 = useT();
    const { rtl } = useLocale();
    const { apps } = useHomebrew();
    const { openGame, push } = useNavActions();
    // Icons load only up to a few cards past the furthest one reached.
    const [reach, setReach] = (0, useState)(FIRST_ART);
    if (!apps.length) return null;
    const shown = apps.slice(0, SHOWN);
    const seeAll = (from) => push({ name: "homebrew" }, from);
    return /* @__PURE__ */ (0, jsxs)(GameRail, { title: t2("nav.homebrew"), onSeeAll: () => seeAll("homebrew:all"), seeAllKey: "homebrew:all", children: [
      shown.map((app, index) => {
        const key = `homebrew:${app.id}`;
        return /* @__PURE__ */ (0, jsx)(GameCard, {
          game: app,
          width: WIDTH,
          detailed: true,
          focusKey: key,
          deferArt: index >= reach,
          onFocus: () => setReach((count) => Math.max(count, index + ART_AHEAD)),
          onPress: () => openGame(app.id, key)
        }, app.id);
      }),
      /* @__PURE__ */ (0, jsx)(View, { ...focusEnd(rtl, MORE_KEY), focusKey: MORE_KEY, onPress: () => seeAll(MORE_KEY), children: /* @__PURE__ */ (0, jsx)(MoreCard, { apps: apps.slice(0, 4), count: apps.length }) })
    ] });
  });

export { HomebrewRail };
