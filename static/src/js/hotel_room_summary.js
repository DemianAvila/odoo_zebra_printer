odoo.define("production_manager.resumen_production", function (require) {
    "use strict";

    var core = require("web.core");
    var registry = require("web.field_registry");
    var basicFields = require("web.basic_fields");
    var FieldText = basicFields.FieldText;
    var QWeb = core.qweb;
    var FormView = require("web.FormView");
    var py = window.py;

    var MyWidget = FieldText.extend({
        events: _.extend({}, FieldText.prototype.events, {
            change: "_onFieldChanged",
        }),
        init: function () {
            this._super.apply(this, arguments);
            if (this.mode === "edit") {
                this.tagName = "span";
            }
            this.set({
                date_to: false,
                date_from: false,
                summary_header: false,
                product_summary: false,
            });
            this.set({
                summary_header: py.eval(this.recordData.summary_header),
            });
            this.set({
                product_summary: py.eval(this.recordData.product_summary),
            });
        },
        start: function () {
            var self = this;
            if (self.setting) {
                return;
            }
            if (!this.get("summary_header") || !this.get("product_summary")) {
                return;
            }
            this.renderElement();
            this.view_loading();
        },
        initialize_field: function () {
            FormView.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            self.on("change:summary_header", self, self.start);
            self.on("change:product_summary", self, self.start);
        },
        view_loading: function (r) {
            return this.load_form(r);
        },

        load_form: function () {
            var self = this;
            this.$el.find(".table_free").bind("click", function () {
                self.do_action({
                    type: "ir.actions.act_window",
                    res_model: "quick.resumen.production",
                    views: [[false, "form"]],
                    target: "new",
                    context: {
//                        room_id: $(this).attr("data"),
                        product_id: $(this).attr("data"),
                        date: $(this).attr("date"),
//                        default_adults: 1,
                    },
                });
            });
        },
        renderElement: function () {
            this._super();
            this.$el.html(
                QWeb.render("RoomSummary", {
                    widget: this,
                })
            );
        },
        _onFieldChanged: function (event) {
            this._super();
            this.lastChangeEvent = event;
            this.set({
                summary_header: py.eval(this.recordData.summary_header),
            });
            this.set({
                product_summary: py.eval(this.recordData.product_summary),
            });
            this.renderElement();
            this.view_loading();
        },
    });

    registry.add("Room_Reservation", MyWidget);
    return MyWidget;
});
