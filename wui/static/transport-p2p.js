$(function() {

$('#p2p_bootstrap_addform').submit(function() {
    var bsType = $('#p2p_bootstrap_type').val();
    var q = {'bsType': bsType};
    var url = '/_transports/p2p/bootstrap/';
    d2p.sendQuery(url, q, function() {
        d2p.content_goto('/_transports/p2p/');
    });
});

$('.p2p_bootstrap[data-bootstrap-type="manual"]').each(function(i, el) {
    var bsEl = $(el);

    var entryTable = bsEl.find('.p2p_bootstrap_entries');
    var newRow = $('<tr class="p2p_bootstrap_newRow">');

    var transportIds = ['p2p-ipv6-tcp'];
    var inputTransportIds = $('<select>');
    _.each(transportIds, function(ti) {
        var opt = $('<option>');
        opt.attr({'value': ti});
        opt.text(ti);
        inputTransportIds.append(opt);
    });
    var td = $('<td>');
    inputTransportIds.appendTo(td);
    td.appendTo(newRow);

    var inputAddr = $('<input type="text" required="required">');
    inputAddr.attr({'placeholder': d2p.i18n('IP address')});
    var td = $('<td>');
    inputAddr.appendTo(td);
    td.appendTo(newRow);

    var inputPort = $('<input type="text">');
    inputPort.attr({'placeholder': d2p.i18n('Port'), size: 5})
    var td = $('<td>');
    inputPort.appendTo(td);
    var submit = $('<input type="button">');
    submit.attr({value: d2p.i18n('Add entry')});
    submit.appendTo(td);
    td.appendTo(newRow);

    submit.click(function() {
        var entry = {
            'transportId': inputTransportIds.val(),
            'addr': inputAddr.val(),
            'port': inputPort.val()
        };

        var url = '/_transports/p2p/bootstrap/' + bsEl.attr('data-bootstrap-id') + '/manual/entries/';
        d2p.sendQuery(url, entry, function() {
            d2p.content_goto('/_transports/p2p/');
        });
    });
    
    entryTable.find('tbody').append(newRow);
});










$('.p2p_bootstrap[data-bootstrap-type="multicast"]').each(function(i, el) {
    var bsEl = $(el);

    var entryTable = bsEl.find('.p2p_bootstrap_entries');
    
    
    var newRow = $('<tr class="p2p_bootstrap_newRow">');
    
    var entry = {'action': 'last_bootstrap_time'};
    var url = '/_transports/p2p/bootstrap/' + bsEl.attr('data-bootstrap-id') + '/multicast/entries/';
    var data_temp = d2p.i18n("Keine Angabe möglich");
    d2p.sendQuery(url, entry, function(data) {
        data_temp = data['last_bs'];
        
        //d2p.content_goto('/_transports/p2p/');
    });

    
    var last_bootstrap_request =  $('<div>').text(data_temp);
    var td = $('<td>');
    last_bootstrap_request.appendTo(td);
    td.appendTo(newRow);
    entryTable.find('tbody').append(newRow);
    
    
    var newRow = $('<tr class="p2p_bootstrap_newRow">');

    var refresh = $('<input type="button">');
    refresh.attr({value: d2p.i18n('Refresh')});
    refresh.click(function() {
        document.location.reload(true)
    });
    var td = $('<td>');
    refresh.appendTo(td);
    td.appendTo(newRow);
    
    
    var start_mc_bs_period = $('<input type="button">');
    start_mc_bs_period.attr({value: d2p.i18n('Start Period')});
    start_mc_bs_period.click(function() {
        var entry = {'action': 'start'};
        var url = '/_transports/p2p/bootstrap/' + bsEl.attr('data-bootstrap-id') + '/multicast/entries/';
        d2p.sendQuery(url, entry, function() {
            d2p.content_goto('/_transports/p2p/');
        });
    });
    var td = $('<td>');
    start_mc_bs_period.appendTo(td);
    td.appendTo(newRow);


    var start_mc_bs = $('<input type="button">');
    start_mc_bs.attr({value: d2p.i18n('Start Permanently')});
    start_mc_bs.click(function() {
        
        var entry = {'action': 'start'};
        var url = '/_transports/p2p/bootstrap/' + bsEl.attr('data-bootstrap-id') + '/multicast/entries/';
        d2p.sendQuery(url, entry, function() {
            d2p.content_goto('/_transports/p2p/');
            //start_mc_bs_period.attr("disabled", "disabled");
        });
    });
    
    var td = $('<td>');
    start_mc_bs.appendTo(td);

    var stop_mc_bs = $('<input type="button">');
    stop_mc_bs.attr({value: d2p.i18n('Stop')});
    stop_mc_bs.click(function() {
        var entry = {'action': 'stop'};
        var url = '/_transports/p2p/bootstrap/' + bsEl.attr('data-bootstrap-id') + '/multicast/entries/';
        d2p.sendQuery(url, entry, function() {
            d2p.content_goto('/_transports/p2p/');
        });
    });
    stop_mc_bs.appendTo(td);
    td.appendTo(newRow);


    entryTable.find('tbody').append(newRow);
});



});
