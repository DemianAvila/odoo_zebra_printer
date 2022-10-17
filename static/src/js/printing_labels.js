odoo.define('client_act.sale_cust', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var PrintingAction = AbstractAction.extend({
        events: {
        },
        init: function(parent, action) {
            this._super(parent, action);
        },
        start: function() {
            rpc.query({
                model: 'printer.wizard',
                method: 'get_labels',
                args: [{}]
            }).then(function(data){
		console.log(data);	
                printJS({printable: data.file, type: 'pdf', base64: true})
                //REDIRECT WHEN PRINT
		//let full_url = window.location.href;
                //let home = full_url.slice(0, (full_url.indexOf("web")+3));
                //console.log(home);
                //window.location.replace(home);
            })
        },
    });
    core.action_registry.add("print_label", PrintingAction);
    return PrintingAction;
 });
