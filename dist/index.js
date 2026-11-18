const manifest = {"name":"Decky Color Lab"};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const callable = api.callable;
const toaster = api.toaster;
const definePlugin = (fn) => {
    return (...args) => {
        return fn(...args);
    };
};

var DefaultContext = {
  color: undefined,
  size: undefined,
  className: undefined,
  style: undefined,
  attr: undefined
};
var IconContext = SP_REACT.createContext && /*#__PURE__*/SP_REACT.createContext(DefaultContext);

var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(e, t) { if (null == e) return {}; var o, r, i = _objectWithoutPropertiesLoose(e, t); if (Object.getOwnPropertySymbols) { var n = Object.getOwnPropertySymbols(e); for (r = 0; r < n.length; r++) o = n[r], -1 === t.indexOf(o) && {}.propertyIsEnumerable.call(e, o) && (i[o] = e[o]); } return i; }
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (-1 !== e.indexOf(n)) continue; t[n] = r[n]; } return t; }
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), true).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: true, configurable: true, writable: true }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r); if ("object" != typeof i) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
  return tree && tree.map((node, i) => /*#__PURE__*/SP_REACT.createElement(node.tag, _objectSpread({
    key: i
  }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
  return props => /*#__PURE__*/SP_REACT.createElement(IconBase, _extends({
    attr: _objectSpread({}, data.attr)
  }, props), Tree2Element(data.child));
}
function IconBase(props) {
  var elem = conf => {
    var attr = props.attr,
      size = props.size,
      title = props.title,
      svgProps = _objectWithoutProperties(props, _excluded);
    var computedSize = size || conf.size || "1em";
    var className;
    if (conf.className) className = conf.className;
    if (props.className) className = (className ? className + " " : "") + props.className;
    return /*#__PURE__*/SP_REACT.createElement("svg", _extends({
      stroke: "currentColor",
      fill: "currentColor",
      strokeWidth: "0"
    }, conf.attr, attr, svgProps, {
      className: className,
      style: _objectSpread(_objectSpread({
        color: props.color || conf.color
      }, conf.style), props.style),
      height: computedSize,
      width: computedSize,
      xmlns: "http://www.w3.org/2000/svg"
    }), title && /*#__PURE__*/SP_REACT.createElement("title", null, title), props.children);
  };
  return IconContext !== undefined ? /*#__PURE__*/SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}

// THIS FILE IS AUTO GENERATED
function FaPalette (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M204.3 5C104.9 24.4 24.8 104.3 5.2 203.4c-37 187 131.7 326.4 258.8 306.7 41.2-6.4 61.4-54.6 42.5-91.7-23.1-45.4 9.9-98.4 60.9-98.4h79.7c35.8 0 64.8-29.6 64.9-65.3C511.5 97.1 368.1-26.9 204.3 5zM96 320c-17.7 0-32-14.3-32-32s14.3-32 32-32 32 14.3 32 32-14.3 32-32 32zm32-128c-17.7 0-32-14.3-32-32s14.3-32 32-32 32 14.3 32 32-14.3 32-32 32zm128-64c-17.7 0-32-14.3-32-32s14.3-32 32-32 32 14.3 32 32-14.3 32-32 32zm128 64c-17.7 0-32-14.3-32-32s14.3-32 32-32 32 14.3 32 32-14.3 32-32 32z"},"child":[]}]})(props);
}

const getState = callable("get_state");
const configure = callable("configure");
const analyze = callable("analyze");
const presets = [{ data: "cinema", label: "Кино" }, { data: "game", label: "Игры" }, { data: "soft", label: "Мягкий" },
    { data: "black", label: "Глубокий чёрный" }, { data: "hdr", label: "Псевдо-HDR · SDR" }];
function Content() {
    const [state, setState] = SP_REACT.useState(null);
    const pending = SP_REACT.useRef(false);
    const timer = SP_REACT.useRef(null);
    const notify = (error) => toaster.toast({ title: "Color Lab", body: String(error) });
    SP_REACT.useEffect(() => {
        let mounted = true;
        const refresh = () => getState().then(s => { if (mounted && !pending.current)
            setState(s); }).catch(notify);
        refresh();
        const id = setInterval(refresh, 2500);
        return () => { mounted = false; clearInterval(id); if (timer.current)
            clearTimeout(timer.current); };
    }, []);
    const update = async (changes) => {
        pending.current = true;
        try {
            setState(await configure(changes));
        }
        catch (error) {
            notify(error);
        }
        finally {
            pending.current = false;
        }
    };
    const slider = (key, value) => {
        setState(s => s ? { ...s, [key]: value } : s);
        pending.current = true;
        if (timer.current)
            clearTimeout(timer.current);
        timer.current = setTimeout(() => { void update({ [key]: value }); }, 180);
    };
    if (!state)
        return SP_JSX.jsx(DFL.PanelSection, { children: SP_JSX.jsx(DFL.PanelSectionRow, { children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430 \u043F\u0440\u043E\u0444\u0438\u043B\u044F\u2026" }) });
    return SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: state.display.internal ? "Встроенный экран" : "Внешний экран", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { fontSize: 12, opacity: .7 }, children: [state.display.name, " \u00B7 ", state.application.name] }) }), state.application.key !== "steam" && SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u0422\u0438\u043F \u043F\u0440\u0438\u043B\u043E\u0436\u0435\u043D\u0438\u044F", description: "\u0412\u0438\u0434\u0435\u043E: \u00AB\u041A\u0438\u043D\u043E\u00BB, \u043F\u0441\u0435\u0432\u0434\u043E-HDR \u0438 \u043C\u0433\u043D\u043E\u0432\u0435\u043D\u043D\u0430\u044F \u043F\u043E\u0434\u0441\u0442\u0440\u043E\u0439\u043A\u0430 \u043F\u0440\u0438 \u0441\u043C\u0435\u043D\u0435 \u0441\u0446\u0435\u043D\u044B. \u0418\u0433\u0440\u0430: \u0438\u0433\u0440\u043E\u0432\u0430\u044F \u043F\u0440\u0435\u0434\u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0430.", rgOptions: [{ data: "game", label: "Игра" }, { data: "video", label: "Фильмы и видео" }], selectedOption: state.kind, onChange: v => void update({ kind: v.data }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "\u0426\u0432\u0435\u0442\u043E\u043A\u043E\u0440\u0440\u0435\u043A\u0446\u0438\u044F", checked: state.enabled, onChange: v => void update({ enabled: v }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u041F\u0440\u0435\u0434\u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043A\u0430", rgOptions: presets, selectedOption: state.preset, onChange: v => void update({ preset: v.data }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.SliderField, { label: "\u0421\u0438\u043B\u0430 \u043E\u0431\u0440\u0430\u0431\u043E\u0442\u043A\u0438", value: state.strength, min: 0, max: 100, step: 5, showValue: true, valueSuffix: "%", onChange: v => slider("strength", v) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.SliderField, { label: "\u0413\u043B\u0443\u0431\u0438\u043D\u0430 \u0447\u0451\u0440\u043D\u043E\u0433\u043E", value: state.black, min: 0, max: 30, step: 2, showValue: true, valueSuffix: "%", onChange: v => slider("black", v) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void update({ enabled: !state.enabled }), children: state.enabled ? "Сравнить: выключить" : "Сравнить: включить" }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u041D\u0435\u0439\u0440\u043E\u0441\u0435\u0442\u0435\u0432\u0430\u044F \u0430\u0434\u0430\u043F\u0442\u0430\u0446\u0438\u044F", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u041C\u043E\u0434\u0435\u043B\u044C", rgOptions: [{ data: "adaptive", label: "Адаптивный цвет · 3DLUT" }, { data: "hdr", label: "SDR → HDR → SDR · HDRTVNet++" }], selectedOption: state.model_id, onChange: v => void update({ model_id: v.data }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u0418\u0441\u043F\u043E\u043B\u043D\u0438\u0442\u0435\u043B\u044C", rgOptions: [{ data: "cpu", label: "CPU · эталон" }, ...((state.model_id !== "hdr" || state.hdr_npu_available) ? [{ data: "npu", label: "CPU + NPU · эксперимент" }] : [])], selectedOption: state.engine, onChange: v => void update({ engine: v.data }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: 12, opacity: .8 }, children: state.model }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "\u0410\u0432\u0442\u043E\u0430\u043D\u0430\u043B\u0438\u0437 \u0441\u0446\u0435\u043D\u044B", description: state.interval ? `Не чаще одного раза в ${state.interval} с; коэффициенты усредняются.` : `Авто: сейчас раз в ${state.interval_effective} с (1–10 с по динамике картинки).`, checked: state.auto, onChange: v => void update({ auto: v }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "\u041C\u0433\u043D\u043E\u0432\u0435\u043D\u043D\u043E \u043F\u0440\u0438 \u0441\u043C\u0435\u043D\u0435 \u0441\u0446\u0435\u043D\u044B", description: "\u041B\u0451\u0433\u043A\u0430\u044F \u043F\u0440\u043E\u0432\u0435\u0440\u043A\u0430 \u043A\u0430\u0434\u0440\u0430 2 \u0440\u0430\u0437\u0430 \u0432 \u0441\u0435\u043A\u0443\u043D\u0434\u0443 \u043D\u0430 CPU; \u043D\u0435\u0439\u0440\u043E\u0441\u0435\u0442\u044C \u0437\u0430\u043F\u0443\u0441\u043A\u0430\u0435\u0442\u0441\u044F \u0441\u0440\u0430\u0437\u0443 \u043F\u0440\u0438 \u0441\u043C\u0435\u043D\u0435 \u0441\u0446\u0435\u043D\u044B.", disabled: !state.auto, checked: state.tracking, onChange: v => void update({ tracking: v }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u0418\u043D\u0442\u0435\u0440\u0432\u0430\u043B \u0430\u043D\u0430\u043B\u0438\u0437\u0430", rgOptions: [{ data: 0, label: "Авто (по динамике сцены)" }, ...[1, 2, 5, 10, 15, 30, 60].map(n => ({ data: n, label: `Раз в ${n} с` }))], selectedOption: state.interval, onChange: v => void update({ interval: v.data }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", disabled: state.busy || !state.enabled, onClick: async () => { pending.current = true; try {
                                setState(await analyze(true));
                            }
                            catch (e) {
                                notify(e);
                            }
                            finally {
                                pending.current = false;
                            } }, children: state.busy ? "Анализ сцены…" : "Проанализировать сейчас" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { fontSize: 12, opacity: .7 }, children: [state.last_analysis ? `Последний анализ: ${new Date(state.last_analysis * 1000).toLocaleTimeString()}` : "Применена подготовленная цветовая таблица", state.analysis_ms != null ? ` · ${state.analysis_ms.toFixed(1)} мс${state.analysis_cpu_ms != null ? ` (CPU: ${state.analysis_cpu_ms.toFixed(1)} мс)` : ""}` : ""] }) }), state.cycle_ms != null && SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { fontSize: 12, opacity: .7 }, children: ["\u041F\u043E\u043B\u043D\u044B\u0439 \u0444\u043E\u043D\u043E\u0432\u044B\u0439 \u0446\u0438\u043A\u043B: ", (state.cycle_ms / 1000).toFixed(2), " \u0441.", state.cycle_cpu_ms != null ? ` CPU плагина ≈ ${state.cycle_cpu_ms.toFixed(1)} мс` : "", ". \u042D\u0442\u043E \u043D\u0435 \u0432\u0440\u0435\u043C\u044F \u043A\u0430\u0434\u0440\u0430."] }) }), state.waiting && SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: 12, opacity: .7 }, children: "\u041E\u0436\u0438\u0434\u0430\u043D\u0438\u0435 \u043D\u043E\u0432\u043E\u0433\u043E \u043A\u0430\u0434\u0440\u0430 \u043F\u0440\u0438\u043B\u043E\u0436\u0435\u043D\u0438\u044F\u2026" }) }), state.last_error && SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: 12, color: "#f0b45e" }, children: state.last_error }) })] }), SP_JSX.jsx(DFL.PanelSection, { title: "\u0421\u043E\u0441\u0442\u043E\u044F\u043D\u0438\u0435", children: SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { fontSize: 12, opacity: .7 }, children: ["\u041E\u0431\u0435 \u043C\u043E\u0434\u0435\u043B\u0438 \u0432\u044B\u0432\u043E\u0434\u044F\u0442 SDR. HDRTVNet++: \u0433\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u0430\u044F \u043D\u0435\u0439\u0440\u043E\u0441\u0435\u0442\u0435\u0432\u0430\u044F HDR-\u0440\u0435\u043A\u043E\u043D\u0441\u0442\u0440\u0443\u043A\u0446\u0438\u044F \u0441 \u0442\u043E\u043D\u0430\u043B\u044C\u043D\u044B\u043C \u043F\u0440\u0435\u043E\u0431\u0440\u0430\u0437\u043E\u0432\u0430\u043D\u0438\u0435\u043C \u0432 SDR; \u0431\u0435\u0437 \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u043E\u0433\u043E \u0432\u043E\u0441\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u0438\u044F \u0434\u0435\u0442\u0430\u043B\u0435\u0439. \u0417\u0430\u0445\u0432\u0430\u0442 PipeWire \u0431\u0435\u0437 \u0441\u043A\u0440\u0438\u043D\u0448\u043E\u0442\u043E\u0432. \u041F\u0440\u043E\u0444\u0438\u043B\u044C \u0441\u043E\u0445\u0440\u0430\u043D\u044F\u0435\u0442\u0441\u044F \u0434\u043B\u044F \u0442\u0435\u043A\u0443\u0449\u0435\u0433\u043E \u043F\u0440\u0438\u043B\u043E\u0436\u0435\u043D\u0438\u044F \u0438 \u044D\u043A\u0440\u0430\u043D\u0430.", state.battery_w != null ? ` Батарея: ${state.battery_w.toFixed(1)} Вт (вся приставка).` : ""] }) }) })] });
}
var index = definePlugin(() => ({ name: "Decky Color Lab", titleView: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "Color Lab" }), content: SP_JSX.jsx(Content, {}), icon: SP_JSX.jsx(FaPalette, {}), onDismount() { } }));

export { index as default };
//# sourceMappingURL=index.js.map
